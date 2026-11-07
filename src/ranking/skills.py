"""Technology/skill extraction and overlap with the candidate's own skills.

Compared with a whole-document word-cosine, this answers a concrete question:
"of the technologies this role actually asks for, how many does the candidate
already know?" Mentions in the title and requirements count more than mentions
in company boilerplate, and related technologies earn partial credit
(Vue ~ React, GCP ~ AWS, Kotlin ~ Java).
"""

import re
from collections import defaultdict
from dataclasses import dataclass, field

from src.ranking.text_clean import split_sections


# canonical skill -> (regex, weight). Weight reflects how defining a skill is:
# generic tooling like git should never dominate a language or framework.
_SKILL_PATTERNS: dict[str, tuple[str, float]] = {
    # languages
    "python": (r"\bpython\b", 1.0),
    "java": (r"\bjava\b", 1.0),
    "javascript": (r"\bjavascript\b|\becmascript\b", 1.0),
    "typescript": (r"\btypescript\b", 1.0),
    "c++": (r"\bc\+\+", 1.0),
    "c#": (r"\bc#|\bcsharp\b", 1.0),
    "go": (
        r"(?i:\bgolang\b)"
        # Capitalised "Go" in a list of technologies ("with Go, Java", "in Go and Rust")
        r"|(?:(?<=[,/(:] )|(?<=[,/(:])|(?<=with )|(?<=in )|(?<=using )|(?<=and )|(?<=or ))"
        r"Go(?=\s*[,/);.]|\s+(?:and|or)\b|\s*$)"
        r"|\bGo\s+(?:programming|language|services|backend)\b",
        1.0,
    ),
    "rust": (r"\brust\b", 1.0),
    "kotlin": (r"\bkotlin\b", 1.0),
    "swift": (r"\bswift\b", 1.0),
    "scala": (r"\bscala\b", 1.0),
    "ruby": (r"\bruby\b", 1.0),
    "php": (r"\bphp\b", 1.0),
    "sql": (r"\bsql\b", 0.9),
    # web / frameworks
    "react": (r"\breact(?:\.?js)?\b", 1.0),
    "nextjs": (r"\bnext\.?js\b", 0.8),
    "vue": (r"\bvue(?:\.?js)?\b", 0.9),
    "angular": (r"\bangular(?:js)?\b", 0.9),
    "nodejs": (r"\bnode\.?js\b|\bnode\b(?=\s*[,/)])", 1.0),
    "graphql": (r"\bgraphql\b", 0.8),
    "rest": (r"\brest(?:ful)?\s+(?:apis?|services|endpoints|interfaces)\b|\brestful\b", 0.8),
    "django": (r"\bdjango\b", 0.9),
    "flask": (r"\bflask\b", 0.8),
    "fastapi": (r"\bfastapi\b", 0.8),
    "spring": (r"\bspring(?:\s*boot)?\b(?=.{0,20}(?:java|boot|framework))|\bspring boot\b", 0.9),
    "rails": (r"\bruby on rails\b|\brails\b", 0.9),
    "dotnet": (r"\.net\b|\bdotnet\b|\basp\.net\b", 0.9),
    "html_css": (r"\bhtml5?\b|\bcss3?\b", 0.5),
    # data
    "postgresql": (r"\bpostgres(?:ql)?\b", 1.0),
    "mysql": (r"\bmysql\b|\bmariadb\b", 0.9),
    "mongodb": (r"\bmongo(?:db)?\b", 0.9),
    "redis": (r"\bredis\b", 0.8),
    "kafka": (r"\bkafka\b", 0.9),
    "spark": (r"\bapache spark\b|\bpyspark\b|\bspark\b(?=.{0,30}(?:data|job|cluster|sql))", 0.9),
    "airflow": (r"\bairflow\b", 0.8),
    "dbt": (r"\bdbt\b", 0.7),
    "bigquery": (r"\bbigquery\b", 0.7),
    "elasticsearch": (r"\belasticsearch\b|\bopensearch\b", 0.8),
    "dynamodb": (r"\bdynamodb\b", 0.7),
    "nosql": (r"\bnosql\b", 0.6),
    "data_pipelines": (r"\bdata pipelines?\b|\betl\b|\belt\b", 0.8),
    # cloud / devops
    "aws": (r"\baws\b|\bamazon web services\b", 1.0),
    "gcp": (r"\bgcp\b|\bgoogle cloud\b", 1.0),
    "azure": (r"\bazure\b", 1.0),
    "docker": (r"\bdocker\b|\bcontainers?\b", 0.9),
    "kubernetes": (r"\bkubernetes\b|\bk8s\b", 0.9),
    "terraform": (r"\bterraform\b|\binfrastructure as code\b", 0.8),
    "cicd": (r"\bci\s*/\s*cd\b|\bcontinuous (?:integration|delivery|deployment)\b|\bgithub actions\b|\bjenkins\b", 0.6),
    "linux": (r"\blinux\b|\bunix\b", 0.6),
    "git": (r"\bgit\b|\bgithub\b|\bgitlab\b", 0.3),
    "microservices": (r"\bmicroservices?\b", 0.7),
    "distributed_systems": (r"\bdistributed systems?\b", 0.8),
    # machine learning / AI
    "machine_learning": (r"\bmachine learning\b|\bml\b", 1.0),
    "deep_learning": (r"\bdeep learning\b|\bneural networks?\b", 0.9),
    "nlp": (r"\bnlp\b|\bnatural language processing\b", 0.9),
    "llm": (r"\bllms?\b|\blarge language models?\b|\bgenerative ai\b|\bgenai\b", 1.0),
    "pytorch": (r"\bpytorch\b|\btorch\b", 1.0),
    "tensorflow": (r"\btensorflow\b|\bkeras\b|\bjax\b", 0.9),
    "huggingface": (r"\bhugging\s?face\b|\btransformers\b", 0.9),
    "rag": (r"\brag\b|\bretrieval[\s-]augmented\b|\bvector (?:database|search|store)s?\b|\bembeddings?\b", 0.8),
    "prompting": (r"\bprompt engineering\b|\bprompting\b|\bfine[\s-]?tun(?:e|ing)\b|\bevals?\b", 0.8),
    "computer_vision": (r"\bcomputer vision\b", 0.8),
    "mlops": (r"\bmlops\b|\bmodel (?:serving|deployment)\b", 0.7),
    "mcp": (r"\bmcp\b|\bmodel context protocol\b", 0.9),
    # general engineering
    "testing": (r"\bunit tests?\b|\bunit testing\b|\bpytest\b|\bjest\b|\bjunit\b|\btest[\s-]driven\b|\bintegration tests?\b", 0.5),
    "api_design": (r"\bapis?\b", 0.6),
    "oauth": (r"\boauth\b|\bsso\b|\bcognito\b|\bauthentication\b", 0.4),
}

# Internal skill key -> how it reads in an email or report.
_DISPLAY_NAMES = {
    "python": "Python", "java": "Java", "javascript": "JavaScript", "typescript": "TypeScript",
    "c++": "C++", "c#": "C#", "go": "Go", "rust": "Rust", "kotlin": "Kotlin", "swift": "Swift",
    "scala": "Scala", "ruby": "Ruby", "php": "PHP", "sql": "SQL", "react": "React",
    "nextjs": "Next.js", "vue": "Vue", "angular": "Angular", "nodejs": "Node.js",
    "graphql": "GraphQL", "rest": "REST", "django": "Django", "flask": "Flask",
    "fastapi": "FastAPI", "spring": "Spring", "rails": "Rails", "dotnet": ".NET",
    "html_css": "HTML/CSS", "postgresql": "PostgreSQL", "mysql": "MySQL", "mongodb": "MongoDB",
    "redis": "Redis", "kafka": "Kafka", "spark": "Spark", "airflow": "Airflow", "dbt": "dbt",
    "bigquery": "BigQuery", "elasticsearch": "Elasticsearch", "dynamodb": "DynamoDB",
    "nosql": "NoSQL", "data_pipelines": "Data Pipelines", "aws": "AWS", "gcp": "GCP",
    "azure": "Azure", "docker": "Docker", "kubernetes": "Kubernetes", "terraform": "Terraform",
    "cicd": "CI/CD", "linux": "Linux", "git": "Git", "microservices": "Microservices",
    "distributed_systems": "Distributed Systems", "machine_learning": "Machine Learning",
    "deep_learning": "Deep Learning", "nlp": "NLP", "llm": "LLMs", "pytorch": "PyTorch",
    "tensorflow": "TensorFlow", "huggingface": "Hugging Face", "rag": "RAG / Embeddings",
    "prompting": "Prompting / Evals", "computer_vision": "Computer Vision", "mlops": "MLOps",
    "mcp": "MCP", "testing": "Testing", "api_design": "APIs", "oauth": "Authentication",
}


def display_name(skill: str) -> str:
    return _DISPLAY_NAMES.get(skill, skill)


_COMPILED = {
    name: (re.compile(pattern, 0 if name == "go" else re.IGNORECASE), weight)
    for name, (pattern, weight) in _SKILL_PATTERNS.items()
}

# Partial credit for related technologies the candidate does not list.
_ADJACENT: dict[str, dict[str, float]] = {
    "vue": {"react": 0.6}, "angular": {"react": 0.5}, "nextjs": {"react": 0.8},
    "kotlin": {"java": 0.6}, "scala": {"java": 0.5}, "c#": {"java": 0.5},
    "go": {"java": 0.35, "python": 0.3}, "javascript": {"typescript": 0.9},
    "typescript": {"javascript": 0.9}, "mysql": {"postgresql": 0.8, "sql": 0.8},
    "postgresql": {"sql": 0.8, "mysql": 0.8}, "nosql": {"mongodb": 0.7, "redis": 0.6},
    "mongodb": {"nosql": 0.6, "postgresql": 0.4}, "dynamodb": {"nosql": 0.6, "aws": 0.5},
    "gcp": {"aws": 0.6}, "azure": {"aws": 0.6}, "kubernetes": {"docker": 0.6},
    "terraform": {"aws": 0.4, "docker": 0.4}, "tensorflow": {"pytorch": 0.7},
    "pytorch": {"tensorflow": 0.7}, "django": {"fastapi": 0.7, "python": 0.6},
    "flask": {"fastapi": 0.8, "python": 0.6}, "fastapi": {"flask": 0.8, "python": 0.6},
    "rails": {"django": 0.4}, "spring": {"java": 0.7, "fastapi": 0.3},
    "dotnet": {"c#": 0.8}, "rest": {"api_design": 0.8, "fastapi": 0.7},
    "api_design": {"rest": 0.8, "fastapi": 0.6}, "bigquery": {"sql": 0.7},
    "airflow": {"data_pipelines": 0.6, "python": 0.5}, "dbt": {"sql": 0.8},
    "spark": {"python": 0.4, "data_pipelines": 0.5}, "kafka": {"distributed_systems": 0.4},
    "mlops": {"machine_learning": 0.6, "docker": 0.4}, "rag": {"llm": 0.8, "nlp": 0.6},
    "prompting": {"llm": 0.8}, "huggingface": {"nlp": 0.6, "pytorch": 0.6},
    "deep_learning": {"machine_learning": 0.8, "pytorch": 0.7}, "nlp": {"machine_learning": 0.6, "llm": 0.7},
    "cicd": {"git": 0.4, "docker": 0.3}, "microservices": {"docker": 0.4, "rest": 0.4},
    "linux": {"docker": 0.3}, "elasticsearch": {"sql": 0.3, "nosql": 0.5},
}

_SECTION_FACTOR = {
    "requirements": 1.5,
    "responsibilities": 1.0,
    "preferred": 0.7,
    "intro": 0.6,
}
_TITLE_FACTOR = 2.0
_PER_SKILL_CAP = 3.0
# Smoothing toward neutral when a posting names few technologies.
_SMOOTHING = 1.5


def skills_in(text: str) -> set[str]:
    return {name for name, (pattern, _) in _COMPILED.items() if pattern.search(text)}


def candidate_skills(profile_text: str) -> set[str]:
    return skills_in(profile_text)


def job_skill_weights(title: str, clean_text: str) -> dict[str, float]:
    """How strongly each technology is asked for (title > requirements > other)."""
    weights: dict[str, float] = defaultdict(float)

    for skill in skills_in(title):
        weights[skill] += _TITLE_FACTOR

    for section in split_sections(clean_text):
        factor = _SECTION_FACTOR.get(section.kind)
        if factor is None:
            continue  # company/benefits/legal boilerplate
        for skill in skills_in(section.text):
            weights[skill] += factor

    return {skill: min(weight, _PER_SKILL_CAP) for skill, weight in weights.items()}


@dataclass
class SkillMatch:
    score: float = 0.5
    matched: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        if self.matched:
            return "Matching skills: " + ", ".join(display_name(s) for s in self.matched[:4])
        if self.related:
            return "Related skills: " + ", ".join(display_name(s) for s in self.related[:3])
        if self.missing:
            return "Skill gaps: " + ", ".join(display_name(s) for s in self.missing[:3])
        return "Few technologies named"


def _credit(skill: str, candidate: set[str]) -> float:
    if skill in candidate:
        return 1.0
    return max(
        (value for related, value in _ADJACENT.get(skill, {}).items() if related in candidate),
        default=0.0,
    )


def match_skills(job_weights: dict[str, float], candidate: set[str]) -> SkillMatch:
    """Weighted overlap in [0, 1] between a job's technologies and the candidate's."""
    result = SkillMatch()
    numerator = denominator = 0.0
    ranked = sorted(job_weights.items(), key=lambda item: -item[1] * _COMPILED[item[0]][1])

    for skill, weight in ranked:
        effective = weight * _COMPILED[skill][1]
        credit = _credit(skill, candidate)
        denominator += effective
        numerator += effective * credit

        if credit >= 1.0:
            result.matched.append(skill)
        elif credit > 0:
            result.related.append(skill)
        elif weight >= 1.5:
            result.missing.append(skill)

    result.score = (numerator + 0.5 * _SMOOTHING) / (denominator + _SMOOTHING)
    return result
