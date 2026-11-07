from src.ranking.text_clean import clean_description, role_text, split_sections


def test_escaped_html_is_turned_into_plain_text_with_line_breaks():
    raw = "&lt;p&gt;Build &amp;amp; ship APIs&lt;/p&gt;&lt;ul&gt;&lt;li&gt;Python&lt;/li&gt;&lt;li&gt;SQL&lt;/li&gt;&lt;/ul&gt;"

    text = clean_description(raw)

    assert "<" not in text
    assert "&amp;" not in text
    assert "Build & ship APIs" in text
    assert "- Python" in text.splitlines()
    assert "- SQL" in text.splitlines()


def test_comparison_operators_are_not_mistaken_for_tags():
    assert "<3 years" in clean_description("Candidates with <3 years of experience")


def test_curly_quotes_are_normalised_so_headings_match():
    text = clean_description("What you’ll do\nBuild services")

    assert "What you'll do" in text


def test_sections_are_labelled_by_heading():
    text = "About Acme\nWe make things.\nRequirements\n- Python\nPreferred Qualifications\n- Go\nBenefits\n- Snacks"

    kinds = [section.kind for section in split_sections(text)]

    assert kinds == ["about", "requirements", "preferred", "benefits"]


def test_you_will_thrive_heading_is_a_requirements_section():
    text = "In this role, you will:\n- Build things\nYou'll thrive in this role if you:\n- Have 2+ years of experience"

    kinds = [section.kind for section in split_sections(text)]

    assert kinds == ["responsibilities", "requirements"]


def test_role_text_leaves_out_company_boilerplate():
    text = "About Acme\nWe were founded in 1999 and love puppies.\nRequirements\n- Python and SQL\nBenefits\n- Free lunch"

    focused = role_text("Software Engineer", text)

    assert "Python and SQL" in focused
    assert "puppies" not in focused
    assert "Free lunch" not in focused
