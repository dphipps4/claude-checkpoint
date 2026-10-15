#!/usr/bin/env python3
"""Validate docs/graph.json and build docs/knowledge-graph.html from it.

graph.json is the single source of truth. The HTML is a derived artifact and is
safe to delete and regenerate at any time.

The data is inlined into the page rather than fetched because the page is
opened as a file:// URL, and browsers block fetch() of a local JSON file from a
file:// origin.

The page is rendered from the first of these that exists:
  1. docs/graph.template.html in the project (must contain __GRAPH_DATA__).
  2. an existing docs/knowledge-graph.html with a `const DATA = {...};` line,
     patched in place so the rest of its markup is untouched.
  3. the template bundled with this plugin.

A template may also contain __GRAPH_TITLE__, replaced with the graph's title.

Usage:
    python3 build_graph.py [project_dir]           validate, then build
    python3 build_graph.py [project_dir] --check   validate only, write nothing
    python3 build_graph.py [project_dir] --init    create docs/graph.json and
                                                   docs/graph.template.html if
                                                   missing; never overwrites

Requires Python 3.9+ and no third-party packages.
"""
import argparse
import html
import json
import os
import re
import shutil
import sys
from datetime import date, datetime

DATA_PLACEHOLDER = "__GRAPH_DATA__"
TITLE_PLACEHOLDER = "__GRAPH_TITLE__"
# The payload is written on one line, and JSON strings cannot hold a raw
# newline, so the first `};` at the end of a line closes the object.
DATA_RE = re.compile(r"const\s+DATA\s*=\s*\{.*?\};[ \t]*$", re.S | re.M)
NODE_FIELDS = ("type", "label", "stage", "owed", "next", "updated")
STALE_DAYS = 14

HERE = os.path.dirname(os.path.abspath(__file__))
BUNDLED_TEMPLATE = os.path.join(HERE, os.pardir, "templates", "graph.template.html")


def fail(msg):
    print("ERROR: " + msg, file=sys.stderr)
    sys.exit(1)


def load(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as e:
        fail("%s is not valid JSON: %s" % (path, e))


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def validate(g, path):
    """Return (problems, warnings, stale). Problems fail the build."""
    if not isinstance(g, dict):
        fail("%s must hold a JSON object" % path)
    nodes = g.get("nodes")
    links = g.get("links", [])
    if not isinstance(nodes, list):
        fail("%s has no 'nodes' list" % path)
    if not isinstance(links, list):
        fail("%s has a 'links' value that is not a list" % path)

    problems, warnings = [], []
    seen = set()
    for i, n in enumerate(nodes):
        if not isinstance(n, dict):
            problems.append("node %d is not an object" % i)
            continue
        nid = n.get("id")
        if not nid:
            problems.append("node %d has no id" % i)
            continue
        if nid in seen:
            problems.append("duplicate node id: %s" % nid)
        seen.add(nid)
        for f in NODE_FIELDS:
            if f not in n:
                warnings.append("%s is missing field '%s'" % (nid, f))
        stage = n.get("stage")
        if stage is not None and (isinstance(stage, bool) or not isinstance(stage, int)):
            warnings.append("%s has a stage that is not an integer: %r" % (nid, stage))

    for i, l in enumerate(links):
        if not isinstance(l, dict):
            problems.append("link %d is not an object" % i)
            continue
        s, t = l.get("s"), l.get("t")
        if s not in seen:
            problems.append("link source is not a node: %r -> %r" % (s, t))
        if t not in seen:
            problems.append("link target is not a node: %r -> %r" % (s, t))
        if not l.get("k"):
            warnings.append("link %r -> %r has no kind 'k'" % (s, t))

    stale = []
    today = date.today()
    for n in nodes:
        if not isinstance(n, dict) or not n.get("updated"):
            continue
        u = n["updated"]
        try:
            d = datetime.strptime(u, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            warnings.append("%s has an updated value that is not YYYY-MM-DD: %r"
                            % (n.get("id"), u))
            continue
        age = (today - d).days
        if age > STALE_DAYS:
            stale.append((age, n.get("id"), u))

    return problems, warnings, sorted(stale, reverse=True)


def payload_of(g):
    data = json.dumps(g, ensure_ascii=False, separators=(", ", ": "))
    # Keep a "</script>" inside a string value from closing the script element.
    return data.replace("</", "<\\/")


def fill_template(tpl_path, g, payload):
    page = read(tpl_path)
    if DATA_PLACEHOLDER not in page:
        fail("%s has no %s placeholder" % (tpl_path, DATA_PLACEHOLDER))
    title = html.escape(str(g.get("title") or g.get("project") or "Knowledge graph"))
    page = page.replace(TITLE_PLACEHOLDER, title)
    return page.replace(DATA_PLACEHOLDER, payload)


def render(g, docs):
    payload = payload_of(g)
    tpl = os.path.join(docs, "graph.template.html")
    out = os.path.join(docs, "knowledge-graph.html")

    if os.path.exists(tpl):
        page, mode = fill_template(tpl, g, payload), "project template"
    elif os.path.exists(out) and DATA_RE.search(read(out)):
        page = DATA_RE.sub(lambda m: "const DATA = " + payload + ";", read(out), count=1)
        mode = "in place"
    elif os.path.exists(BUNDLED_TEMPLATE):
        page, mode = fill_template(BUNDLED_TEMPLATE, g, payload), "bundled template"
    else:
        fail("no template found: add docs/graph.template.html with a %s placeholder"
             % DATA_PLACEHOLDER)

    with open(out, "w", encoding="utf-8") as fh:
        fh.write(page)
    return out, mode


def init(root, docs, gjson):
    os.makedirs(docs, exist_ok=True)
    name = os.path.basename(root) or "project"
    if os.path.exists(gjson):
        print("exists, left unchanged: %s" % gjson)
    else:
        today = date.today().isoformat()
        skeleton = {"project": name, "title": name, "updated": today,
                    "nodes": [], "links": []}
        with open(gjson, "w", encoding="utf-8") as fh:
            json.dump(skeleton, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        print("created %s" % gjson)

    tpl = os.path.join(docs, "graph.template.html")
    if os.path.exists(tpl):
        print("exists, left unchanged: %s" % tpl)
    elif os.path.exists(BUNDLED_TEMPLATE):
        shutil.copyfile(BUNDLED_TEMPLATE, tpl)
        print("created %s" % tpl)
    else:
        fail("bundled template not found at %s" % os.path.normpath(BUNDLED_TEMPLATE))


def main():
    ap = argparse.ArgumentParser(
        description="Validate docs/graph.json and build docs/knowledge-graph.html.")
    ap.add_argument("project_dir", nargs="?", default=os.getcwd(),
                    help="project root (default: current directory)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true",
                      help="validate only; write nothing")
    mode.add_argument("--init", action="store_true",
                      help="create docs/graph.json and docs/graph.template.html "
                           "if missing; never overwrite")
    args = ap.parse_args()

    root = os.path.abspath(args.project_dir)
    docs = os.path.join(root, "docs")
    gjson = os.path.join(docs, "graph.json")

    if args.init:
        init(root, docs, gjson)
        return
    if not os.path.exists(gjson):
        fail("%s not found. Run with --init to create it." % gjson)

    g = load(gjson)
    problems, warnings, stale = validate(g, gjson)
    for w in warnings:
        print("warn: " + w)
    if problems:
        for p in problems:
            print("ERROR: " + p, file=sys.stderr)
        sys.exit(1)

    print("graph.json ok: %d nodes, %d links" % (len(g["nodes"]), len(g.get("links", []))))
    if stale:
        print("stale (updated more than %d days ago):" % STALE_DAYS)
        for age, nid, u in stale[:15]:
            print("  %-20s %s  (%d days)" % (nid, u, age))

    if args.check:
        return
    out, how = render(g, docs)
    print("wrote %s (%s, %d bytes)" % (out, how, os.path.getsize(out)))


if __name__ == "__main__":
    main()
