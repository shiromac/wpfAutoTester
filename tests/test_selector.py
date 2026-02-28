"""Tests for Selector."""

from wpf_agent.uia.selector import Selector


def test_describe_with_automation_id():
    s = Selector(automation_id="Btn1")
    assert "aid=Btn1" in s.describe()


def test_describe_with_name_and_type():
    s = Selector(name="OK", control_type="Button")
    desc = s.describe()
    assert "name='OK'" in desc
    assert "type=Button" in desc


def test_describe_empty():
    s = Selector()
    assert s.describe() == "(empty selector)"


def test_to_find_kwargs():
    s = Selector(automation_id="Txt1", name="Username", control_type="Edit")
    kw = s.to_find_kwargs()
    assert kw["auto_id"] == "Txt1"
    assert kw["title"] == "Username"
    assert kw["control_type"] == "Edit"


def test_to_find_kwargs_empty():
    s = Selector()
    assert s.to_find_kwargs() == {}


def test_describe_with_index():
    s = Selector(automation_id="Item", index=3)
    assert "idx=3" in s.describe()
