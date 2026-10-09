"""Local Gemma MCP entry point; each public tool lives in its named module."""

import argparse
import os
from pathlib import Path
import tool_config
from search_web import search_web as search_web
from read_web import read_web as read_web
from extract_evidence import extract_evidence as extract_evidence
from inspect_run import inspect_run as inspect_run
from validation_report import validation_report as validation_report
from filter_log import filter_log as filter_log
from search_repository import search_repository as search_repository
from compare_reports import compare_reports as compare_reports
from read_artifact import read_artifact as read_artifact

if __name__ == "__main__":
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-root", type=Path, action="append", required=True)
    args = parser.parse_args()
    tool_config.ROOTS = [root.resolve() for root in args.allow_root]
    tool_config.mcp.run(transport="stdio")
