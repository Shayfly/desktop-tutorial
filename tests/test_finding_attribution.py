from scripts.check_finding_attribution import conflicts


def test_same_agent_cannot_report_and_coauthor_even_with_multiple_trailers():
    message = ('Fix release check\n\n'
               'Found-by: Matt\n'
               'Found-by: Claude Code\n'
               'Co-authored-by: Codex <codex@example.test>\n'
               'Co-authored-by: CLAUDE <claude@example.test>\n')
    assert conflicts(message) == {'claude'}


def test_a_distinct_coauthor_and_body_examples_do_not_conflict():
    message = ('Fix release check\n\n'
               'Found-by: Codex\n'
               'This example belongs to the commit description.\n\n'
               'Found-by: Matt\n'
               'Co-Authored-By: Codex <codex@example.test>\n')
    assert not conflicts(message)
