from app.api.endpoints.assignments import _build_course_layout


def _build_sections(section_type, count, start_nrc):
    return [
        {"seccion": f"{section_type}{idx + 1}", "nrc": str(start_nrc + idx)}
        for idx in range(count)
    ]


def test_leagues_with_practice_as_base():
    desired_counts = {"T": 0, "P": 2, "L": 2}
    sections_by_type = {
        "P": _build_sections("P", 2, 200),
        "L": _build_sections("L", 2, 300),
    }

    session_types, leagues, capacity = _build_course_layout(desired_counts, sections_by_type)

    assert len(session_types) == 2
    assert {detail.session_type for detail in session_types} == {"P", "L"}

    assert len(leagues) == 2
    expected_capacity = {("P", 1): 1, ("L", 1): 1, ("P", 2): 1, ("L", 2): 1}
    for key, value in expected_capacity.items():
        assert capacity[key] == value

    for league in leagues:
        session_map = {session.session_type: session for session in league.sessions}
        assert session_map["P"].section_count == 1
        assert session_map["P"].sections == [f"P{league.league}"]
        assert session_map["L"].section_count == 1
        assert session_map["L"].sections == [f"L{league.league}"]


def test_leagues_with_theory_as_base():
    desired_counts = {"T": 3, "P": 2, "L": 1}
    sections_by_type = {
        "T": _build_sections("T", 3, 100),
        "P": _build_sections("P", 2, 200),
        "L": _build_sections("L", 1, 300),
    }

    session_types, leagues, capacity = _build_course_layout(desired_counts, sections_by_type)

    assert len(session_types) == 3
    assert len(leagues) == 3

    for idx, league in enumerate(leagues, start=1):
        session_map = {session.session_type: session for session in league.sessions}
        assert session_map["T"].section_count == 1
        assert session_map["T"].sections == [f"T{league.league}"]
        assert capacity[("T", league.league)] == 1
        if "P" in session_map:
            assert session_map["P"].section_count == 1
            assert capacity[("P", league.league)] == 1
            assert session_map["P"].sections == [f"P{league.league}"]
        if "L" in session_map:
            assert session_map["L"].section_count == 1
            assert capacity[("L", league.league)] == 1
            assert session_map["L"].sections == [f"L{league.league}"]

    # Esperamos dos prácticas distribuidas en las dos primeras ligas y un laboratorio en la primera liga
    practice_leagues = [league for league in leagues if any(session.session_type == "P" for session in league.sessions)]
    assert len(practice_leagues) == 2
    lab_leagues = [league for league in leagues if any(session.session_type == "L" for session in league.sessions)]
    assert len(lab_leagues) == 1


def test_leagues_with_only_laboratories():
    desired_counts = {"T": 0, "P": 0, "L": 3}
    sections_by_type = {
        "L": _build_sections("L", 3, 300),
    }

    session_types, leagues, capacity = _build_course_layout(desired_counts, sections_by_type)

    assert len(session_types) == 1
    assert session_types[0].session_type == "L"

    assert len(leagues) == 3
    for league in leagues:
        session_map = {session.session_type: session for session in league.sessions}
        assert session_map["L"].section_count == 1
        assert capacity[("L", league.league)] == 1
        assert session_map["L"].sections == [f"L{league.league}"]


def test_placeholder_sections_generate_leagues():
    desired_counts = {"T": 0, "P": 3, "L": 0}
    sections_by_type = {
        "P": _build_sections("P", 2, 200),
    }

    session_types, leagues, capacity = _build_course_layout(desired_counts, sections_by_type)

    assert len(session_types) == 1
    assert session_types[0].section_count == 3

    assert len(leagues) == 3
    for league in leagues:
        session_map = {session.session_type: session for session in league.sessions}
        assert "P" in session_map
        assert session_map["P"].section_count == 1
        assert session_map["P"].sections == [f"P{league.league}"]

    placeholder_leagues = [
        league
        for league in leagues
        if any(
            detail.get("nrc") is None
            for session in league.sessions
            for detail in session.section_details
        )
    ]
    assert len(placeholder_leagues) == 1
    assert capacity[("P", placeholder_leagues[0].league)] == 1
