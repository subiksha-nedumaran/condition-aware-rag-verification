"""Tests for FieldGuard unified command-line interface (CLI)."""

from __future__ import annotations

import argparse
from pathlib import Path

from fieldguard.cli import (
    cmd_evaluate,
    cmd_index_build,
    cmd_retrieve,
    cmd_sources_validate,
    cmd_verify,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_cli_sources_validate() -> None:
    args = argparse.Namespace()
    ret = cmd_sources_validate(args)
    assert ret == 0


def test_cli_index_build() -> None:
    args = argparse.Namespace()
    ret = cmd_index_build(args)
    assert ret == 0


def test_cli_retrieve() -> None:
    args = argparse.Namespace(
        query="What is the maximum farmer premium for Kharif food grains?",
        method="hybrid",
        top_k=3,
        json=True,
    )
    ret = cmd_retrieve(args)
    assert ret == 0


def test_cli_verify_supported() -> None:
    args = argparse.Namespace(
        claim="Under the 2023 PMFBY operational guidelines, the maximum farmer premium for Kharif food grains is 2.0% of Sum Insured.",
        question=None,
        claim_id="TEST_01",
        method="hybrid",
        top_k=3,
        json=True,
    )
    ret = cmd_verify(args)
    assert ret == 0


def test_cli_verify_wrong_context() -> None:
    args = argparse.Namespace(
        claim="Under the 2023 PMFBY operational guidelines, the maximum farmer premium for Kharif food grains is 5.0% of Sum Insured.",
        question=None,
        claim_id="TEST_02",
        method="hybrid",
        top_k=3,
        json=True,
    )
    ret = cmd_verify(args)
    assert ret == 0


def test_cli_evaluate_errors() -> None:
    args = argparse.Namespace(
        eval_target="errors",
        split="test",
        bootstrap_iterations=100,
    )
    ret = cmd_evaluate(args)
    assert ret == 0
