"""
Regression test suite for Smart Element Interaction (Semantic Click, Numeric Click, Smart Fill).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from schemas import local_parse, ActionType, ALLOWED_DOMAINS
from desktop_controller import _smart_click, _smart_fill

def test_schema_decomposition_click():
    plan = local_parse("click Learn More")
    assert plan is not None
    assert len(plan.steps) == 2
    assert plan.steps[0].action == ActionType.CLICK
    assert plan.steps[0].target == "Learn More"
    assert plan.steps[1].action == ActionType.SCREENSHOT

def test_schema_decomposition_numeric_click():
    plan = local_parse("click 1")
    assert plan is not None
    assert len(plan.steps) == 2
    assert plan.steps[0].action == ActionType.CLICK
    assert plan.steps[0].target == "1"
    assert plan.steps[1].action == ActionType.SCREENSHOT

def test_schema_decomposition_type():
    plan = local_parse("type hello world in search box")
    assert plan is not None
    assert len(plan.steps) == 2
    assert plan.steps[0].action == ActionType.FILL
    assert plan.steps[0].target == "hello world"
    assert plan.steps[0].params["selector"] == "search box"
    assert plan.steps[1].action == ActionType.SCREENSHOT

def test_schema_decomposition_inspect():
    plan = local_parse("inspect page")
    assert plan is not None
    assert len(plan.steps) == 1
    assert plan.steps[0].action == ActionType.ARIA_SNAPSHOT

def test_example_domain_allowed():
    assert "example.com" in ALLOWED_DOMAINS
    assert "www.example.com" in ALLOWED_DOMAINS
