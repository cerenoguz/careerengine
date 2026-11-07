from src.ranking.role_fit import assess_role_fit
from src.ranking.skills import candidate_skills, job_skill_weights, match_skills, skills_in

PROFILE = "Python, Java, SQL, React, TypeScript, AWS, Docker, REST APIs, PostgreSQL, LLMs"


def test_skills_are_detected_from_text():
    found = skills_in("We use Python, React, PostgreSQL and Kubernetes on AWS.")

    assert {"python", "react", "postgresql", "kubernetes", "aws"} <= found


def test_go_is_only_detected_as_the_language():
    assert "go" in skills_in("Experience with Go, Java, and Python")
    assert "go" not in skills_in("Go to market with our sales team")
    assert "go" in skills_in("Experience with golang")


def test_requirement_mentions_outweigh_boilerplate_mentions():
    text = "About Acme\nWe love Rust.\nRequirements\n- Python and SQL\n"

    weights = job_skill_weights("Software Engineer", text)

    assert "rust" not in weights
    assert weights["python"] > 0


def test_matching_skills_scores_above_missing_skills():
    candidate = candidate_skills(PROFILE)
    strong = match_skills(job_skill_weights("Backend Engineer", "Requirements\n- Python, SQL, PostgreSQL, AWS"), candidate)
    weak = match_skills(job_skill_weights("Backend Engineer", "Requirements\n- Scala, Kafka, Spark, Terraform"), candidate)

    assert strong.score > 0.7
    assert weak.score < 0.4
    assert "python" in strong.matched


def test_related_technology_earns_partial_credit():
    candidate = candidate_skills(PROFILE)
    result = match_skills(job_skill_weights("Frontend Engineer", "Requirements\n- Vue"), candidate)

    assert "vue" in result.related
    assert result.score > match_skills(job_skill_weights("Frontend Engineer", "Requirements\n- Scala"), candidate).score


def test_a_posting_naming_no_technologies_is_neutral():
    assert match_skills({}, candidate_skills(PROFILE)).score == 0.5


def test_role_fit_prefers_core_software_titles():
    backend = assess_role_fit("Backend Software Engineer")
    swe = assess_role_fit("Software Engineer, New Grad")
    solutions = assess_role_fit("Solutions Engineer")
    hardware = assess_role_fit("Embedded Software Engineer")

    assert backend.score >= swe.score > solutions.score
    assert swe.score > hardware.score


def test_developer_advocate_is_not_an_engineering_role():
    assert assess_role_fit("Developer Advocate - AI & Developer Experiences").score <= 0.3


def test_platform_in_a_non_engineering_title_gets_no_credit():
    assert assess_role_fit("User Experience Researcher, Platform").score == 0.0


def test_unrelated_title_scores_zero():
    assert assess_role_fit("Office Coordinator").score == 0.0
