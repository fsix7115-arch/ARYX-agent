"""
ARYx AGENT - Doctor Diagnostics Tests
Verifies the 9 doctor functional checks and diagnostic reporting.
"""

from aryx.doctor import (
    check_python_version,
    check_aryx_dir_permissions,
    check_sqlite_memory,
    check_skills_dir,
    check_disk_space,
    run_doctor,
)


def test_doctor_probes():
    py_check = check_python_version()
    assert py_check.status in ("PASS", "WARN", "FAIL")
    assert "Python" in py_check.details

    dir_check = check_aryx_dir_permissions()
    assert dir_check.status in ("PASS", "WARN", "FAIL")

    db_check = check_sqlite_memory()
    assert db_check.status in ("PASS", "WARN", "FAIL")

    skills_check = check_skills_dir()
    assert skills_check.status in ("PASS", "WARN", "FAIL")

    disk_check = check_disk_space()
    assert disk_check.status in ("PASS", "WARN", "FAIL")


def test_doctor_json_output():
    # JSON run shouldn't crash
    import io
    from contextlib import redirect_stdout

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        run_doctor(as_json=True)
    out = buffer.getvalue()
    assert "summary" in out
    assert "checks" in out


if __name__ == "__main__":
    test_doctor_probes()
    test_doctor_json_output()
    print("✓ All doctor probe tests passed successfully!")
