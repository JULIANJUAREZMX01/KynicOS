from app.core.skill_engine import _normalize_skill_name, _validate_skill_code


def test_normalize_skill_name():
    assert _normalize_skill_name("Mi Skill-01") == "mi_skill_01"
    assert _normalize_skill_name("../bad/name") == "bad_name"
    assert _normalize_skill_name("123bad") == ""


def test_validate_skill_code_accepts_normal_python():
    assert _validate_skill_code("def run(name='world'):\n    return f'hello {name}'")


def test_validate_skill_code_rejects_dangerous_imports_and_calls():
    assert not _validate_skill_code("import subprocess\nsubprocess.run(['whoami'])")
    assert not _validate_skill_code("import os\nos.system('echo bad')")
    assert not _validate_skill_code("eval('2 + 2')")
    assert not _validate_skill_code("from pathlib import Path\nPath('x').unlink()")


def test_validate_skill_code_rejects_syntax_errors():
    assert not _validate_skill_code("def broken(:\n    pass")
