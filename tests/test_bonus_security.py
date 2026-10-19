
from bonus_injection_demo import list_notes, delete_note


def test_list_notes_does_not_change_data():
    notes = {1: "Learn Python", 2: "Build an MCP server"}

    result = list_notes(notes)

    assert result == notes
    assert notes == {1: "Learn Python", 2: "Build an MCP server"}


def test_delete_requires_confirmation():
    notes = {1: "Learn Python"}

    result = delete_note(notes, 1)

    assert result["success"] is False
    assert 1 in notes


def test_wrong_confirmation_is_rejected():
    notes = {1: "Learn Python"}

    result = delete_note(notes, 1, "YES")

    assert result["success"] is False
    assert 1 in notes


def test_exact_confirmation_allows_deletion():
    notes = {1: "Learn Python"}

    result = delete_note(notes, 1, "DELETE 1")

    assert result["success"] is True
    assert 1 not in notes


def test_cannot_delete_unknown_note():
    notes = {1: "Learn Python"}

    result = delete_note(notes, 99, "DELETE 99")

    assert result["success"] is False
    assert notes == {1: "Learn Python"}
