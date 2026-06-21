#!/usr/bin/env python3
"""
AGNT Course — Markdown to Interactive HTML Converter
Reads .md files from learn/ and produces beautiful interactive .html files.
"""

import re
import os
import sys
from pathlib import Path

COURSE_DIR = Path(__file__).parent.parent
LEARN_DIR = COURSE_DIR / 'learn'
HTML_DIR = COURSE_DIR / 'html'
CSS_REL = '../css/styles.css'
JS_REL = '../js/app.js'

# Module metadata
MODULES = {
    '00-setup': {'week': 'Setup', 'title': 'Environment Setup', 'lang': 'setup', 'desc': 'Install Go, Elixir, Docker, and all tools'},
    '01-go-fundamentals': {'week': 'Week 1', 'title': 'Go Fundamentals', 'lang': 'go', 'desc': 'Variables, types, control flow, functions, structs, interfaces'},
    '02-go-cli-http': {'week': 'Week 2', 'title': 'Go CLI & HTTP', 'lang': 'go', 'desc': 'Cobra CLI, net/http, graceful shutdown, middleware'},
    '03-elixir-fundamentals': {'week': 'Week 3', 'title': 'Elixir Fundamentals', 'lang': 'elixir', 'desc': 'Pattern matching, pipe operator, immutability, Enum'},
    '04-otp-genserver': {'week': 'Week 4', 'title': 'OTP & GenServer', 'lang': 'elixir', 'desc': 'Agent unit, state, messages, lifecycle, supervisors'},
    '05-multi-agent-supervision': {'week': 'Week 5', 'title': 'Multi-Agent Supervision', 'lang': 'elixir', 'desc': 'Supervisor, DynamicSupervisor, Registry, parent-child trees'},
    '06-phoenix-liveview': {'week': 'Week 6', 'title': 'Phoenix LiveView Dashboard', 'lang': 'elixir', 'desc': 'Real-time agent monitoring UI'},
    '07-agent-communication': {'week': 'Week 7', 'title': 'Agent Communication & Signals', 'lang': 'elixir', 'desc': 'Process messages, PubSub, signal envelopes'},
    '08-agent-state-durable': {'week': 'Week 8', 'title': 'Agent State & Durable Workflows', 'lang': 'elixir', 'desc': 'ETS, Ecto, Oban jobs, persistence'},
    '09-advanced-otp': {'week': 'Week 9', 'title': 'Advanced OTP Patterns', 'lang': 'elixir', 'desc': 'gen_statem, Task.Supervisor, GenStage, Broadway'},
    '10-clustering-distribution': {'week': 'Week 10', 'title': 'Clustering & Distribution', 'lang': 'elixir', 'desc': 'libcluster, Erlang distribution, Horde'},
    '11-go-k8s-operators': {'week': 'Week 11', 'title': 'Go K8s Operators', 'lang': 'go', 'desc': 'controller-runtime, reconciler, CRDs'},
    '12-go-prometheus': {'week': 'Week 12', 'title': 'Go Prometheus Exporters', 'lang': 'go', 'desc': 'client_golang, custom metrics, RED'},
    '13-grpc-bridge': {'week': 'Week 13', 'title': 'Bridge: gRPC', 'lang': 'both', 'desc': 'Protobuf contracts, cross-language types'},
    '14-observability-stack': {'week': 'Week 14', 'title': 'Observability Stack', 'lang': 'both', 'desc': 'OpenTelemetry, Grafana, LiveDashboard'},
    '15-production-deployment': {'week': 'Week 15', 'title': 'Production Deployment', 'lang': 'both', 'desc': 'Docker, K8s, Helm, Terraform'},
    '16-capstone': {'week': 'Week 16', 'title': 'Capstone: Agentic Platform', 'lang': 'both', 'desc': 'Complete platform combining everything'},
}

LANG_LABELS = {'go': 'Go', 'elixir': 'Elixir', 'both': 'Both', 'setup': 'Setup'}


# ─── Single-Pass Tokenizer ───
# Strategy: Match all tokens in ONE pass. First match wins.
# This prevents later regexes from matching inside already-matched spans.

def _escape_html(code):
    return code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _tokenize(code, token_patterns):
    """Single-pass tokenizer. token_patterns: list of (regex, css_class).
    First match wins — no nested/wrapping issues."""
    # Build a combined regex with named groups
    combined = '|'.join(f'(?P<g{i}>{pat})' for i, (pat, _) in enumerate(token_patterns))

    def replacer(m):
        for i, (_, css_class) in enumerate(token_patterns):
            if m.group(f'g{i}') is not None:
                return f'<span class="{css_class}">{m.group(0)}</span>'
        return m.group(0)

    return re.sub(combined, replacer, code, flags=re.MULTILINE | re.DOTALL)


def highlight_go(code):
    """Single-pass Go syntax highlighting."""
    code = _escape_html(code)
    return _tokenize(code, [
        (r'/\*.*?\*/', 'token-comment'),           # multi-line comment
        (r'//[^\n]*', 'token-comment'),              # single-line comment
        (r'"(?:[^"\\]|\\.)*"', 'token-string'),     # double-quoted string
        (r'`[^`]*`', 'token-string'),                # raw string
        (r'\b(?:package|import|func|return|if|else|for|range|switch|case|default|var|const|type|struct|interface|map|chan|go|defer|select|break|continue|fallthrough|nil|true|false|iota|make|new|len|cap|append|copy|delete|close|panic|recover|print|println)\b', 'token-keyword'),
        (r'\b(?:int|int8|int16|int32|int64|uint|uint8|uint16|uint32|uint64|float32|float64|string|bool|byte|rune|error|any)\b', 'token-type'),
        (r'\b\d[\d_]*\.?\d*\b', 'token-number'),
        (r'\b[A-Z]\w*\s*(?=\()', 'token-function'),
        (r'@\w+', 'token-decorator'),
    ])


def highlight_elixir(code):
    """Single-pass Elixir syntax highlighting."""
    code = _escape_html(code)
    return _tokenize(code, [
        (r'#[^#\n][^\n]*', 'token-comment'),
        (r'"(?:[^"\\]|\\.)*"', 'token-string'),
        (r"'(?:[^'\\]|\\.)*'", 'token-string'),
        (r'\b(?:def|defp|defmodule|defstruct|defprotocol|defimpl|defmacro|defmacrop|use|import|require|alias|cond|case|with|fn|do|end|else|after|rescue|catch|when|and|or|not|in|true|false|nil|self|super|if|unless|raise|try)\b', 'token-keyword'),
        (r':[\w]+[!?]?', 'token-atom'),
        (r'\b[A-Z]\w*(?:\.[A-Z]\w*)*\b', 'token-type'),
        (r'\b\w+(?=\s*\()', 'token-function'),
        (r'\b\d[\d_]*\.?\d*\b', 'token-number'),
        (r'\|&gt;', 'token-operator'),
    ])


def highlight_bash(code):
    """Single-pass Bash syntax highlighting."""
    code = _escape_html(code)
    return _tokenize(code, [
        (r'#[^\n]*', 'token-comment'),
        (r'"(?:[^"\\]|\\.)*"', 'token-string'),
        (r"'(?:[^'\\]|\\.)*'", 'token-string'),
        (r'\b(?:if|then|else|elif|fi|for|do|done|while|until|case|esac|function|return|exit|export|source|local|readonly|unset|shift|set|eval|exec)\b', 'token-keyword'),
        (r'\$\{[^}]+\}|\$\w+', 'token-variable'),
    ])


def highlight_protobuf(code):
    """Single-pass Protobuf syntax highlighting."""
    code = _escape_html(code)
    return _tokenize(code, [
        (r'//[^\n]*', 'token-comment'),
        (r'"(?:[^"\\]|\\.)*"', 'token-string'),
        (r'\b(?:syntax|package|import|service|rpc|returns|message|enum|oneof|map|repeated|optional|stream|option|true|false)\b', 'token-keyword'),
        (r'\b(?:string|int32|int64|uint32|uint64|sint32|sint64|fixed32|fixed64|sfixed32|sfixed64|float|double|bool|bytes)\b', 'token-type'),
        (r'\b\d+\b', 'token-number'),
    ])


def highlight_yaml(code):
    """Single-pass YAML syntax highlighting."""
    code = _escape_html(code)
    return _tokenize(code, [
        (r'#[^\n]*', 'token-comment'),
        (r'"(?:[^"\\]|\\.)*"', 'token-string'),
        (r"'(?:[^'\\]|\\.)*'", 'token-string'),
        (r'^\s*[\w.-]+\s*:', 'token-keyword'),
        (r'\b(?:true|false|null|~)\b', 'token-atom'),
    ])


def highlight_sql(code):
    """Single-pass SQL syntax highlighting."""
    code = _escape_html(code)
    return _tokenize(code, [
        (r'--[^\n]*', 'token-comment'),
        (r"'(?:[^'\\]|\\.)*'", 'token-string'),
        (r'(?i)\b(?:SELECT|FROM|WHERE|INSERT|INTO|VALUES|UPDATE|SET|DELETE|CREATE|TABLE|ALTER|DROP|INDEX|PRIMARY|KEY|FOREIGN|REFERENCES|NOT|NULL|DEFAULT|AUTO_INCREMENT|UNIQUE|CHECK|CONSTRAINT|JOIN|LEFT|RIGHT|INNER|OUTER|ON|AND|OR|IN|EXISTS|BETWEEN|LIKE|ORDER|BY|GROUP|HAVING|LIMIT|OFFSET|AS|DISTINCT|COUNT|SUM|AVG|MIN|MAX|CASE|WHEN|THEN|ELSE|END|BEGIN|COMMIT|ROLLBACK|IF|TYPE|UUID|TIMESTAMP|BOOLEAN|INTEGER|TEXT|VARCHAR|BIGSERIAL|SERIAL|JSONB)\b', 'token-keyword'),
        (r'\b\d+\b', 'token-number'),
    ])


LANGUAGES = {
    'go': highlight_go,
    'elixir': highlight_elixir,
    'bash': highlight_bash,
    'sh': highlight_bash,
    'shell': highlight_bash,
    'protobuf': highlight_protobuf,
    'proto': highlight_protobuf,
    'yaml': highlight_yaml,
    'yml': highlight_yaml,
    'sql': highlight_sql,
}


def highlight_code(code, lang):
    """Apply syntax highlighting to a code block."""
    if lang in LANGUAGES:
        return LANGUAGES[lang](code)
    # Default: just escape HTML
    return _escape_html(code)


# ─── Markdown to HTML Converter ───

def md_to_html(md_text):
    """Convert markdown text to HTML with interactive elements."""
    lines = md_text.split('\n')
    html_parts = []
    in_code_block = False
    code_lang = ''
    code_lines = []
    in_table = False
    table_rows = []
    in_blockquote = False
    blockquote_lines = []
    in_list = False
    list_type = None

    i = 0
    while i < len(lines):
        line = lines[i]

        # Code blocks
        if line.strip().startswith('```'):
            if not in_code_block:
                in_code_block = True
                code_lang = line.strip()[3:].strip()
                code_lines = []
            else:
                # End code block
                code_text = '\n'.join(code_lines)
                highlighted = highlight_code(code_text, code_lang)

                # Extract filename from first comment if present
                filename = ''
                first_line = code_lines[0].strip() if code_lines else ''
                fn_match = re.match(r'//\s*(?:File:\s*)?(.+?\.\w+)', first_line)
                if fn_match:
                    filename = fn_match.group(1)

                html_parts.append(f'''<div class="code-block fade-in">
  <div class="code-header">
    <span class="code-lang">{code_lang}</span>
    {f'<span class="code-filename">{filename}</span>' if filename else ''}
    <button class="code-copy" aria-label="Copy code">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
      Copy
    </button>
  </div>
  <div class="code-body"><pre><code>{highlighted}</code></pre></div>
</div>''')
                in_code_block = False
                code_lang = ''
            i += 1
            continue

        if in_code_block:
            code_lines.append(line)
            i += 1
            continue

        # Tables
        if '|' in line and line.strip().startswith('|'):
            if not in_table:
                in_table = True
                table_rows = []

            # Skip separator rows (|---|---|)
            if re.match(r'^\|[\s\-:|]+\|$', line.strip()):
                i += 1
                continue

            cells = [c.strip() for c in line.strip().split('|')[1:-1]]
            table_rows.append(cells)
            # Check if next line is still table
            if i + 1 < len(lines) and '|' in lines[i + 1] and lines[i + 1].strip().startswith('|'):
                i += 1
                continue
            else:
                # End table
                if table_rows:
                    header = table_rows[0]
                    body = table_rows[1:] if len(table_rows) > 1 else []
                    html_parts.append('<div class="table-wrapper fade-in"><table>')
                    html_parts.append('<thead><tr>')
                    for cell in header:
                        html_parts.append(f'<th>{inline_md(cell)}</th>')
                    html_parts.append('</tr></thead>')
                    if body:
                        html_parts.append('<tbody>')
                        for row in body:
                            html_parts.append('<tr>')
                            for cell in row:
                                html_parts.append(f'<td>{inline_md(cell)}</td>')
                            html_parts.append('</tr>')
                        html_parts.append('</tbody>')
                    html_parts.append('</table></div>')
                in_table = False
                table_rows = []
                i += 1
                continue

        # Blockquotes → callout boxes
        if line.strip().startswith('>'):
            if not in_blockquote:
                in_blockquote = True
                blockquote_lines = []
            content = line.strip()[1:].strip()
            blockquote_lines.append(content)
            # Check if next line is still blockquote
            if i + 1 < len(lines) and lines[i + 1].strip().startswith('>'):
                i += 1
                continue
            else:
                # End blockquote → convert to callout
                text = ' '.join(blockquote_lines)
                # Detect callout type
                callout_type = 'info'
                if any(w in text.lower() for w in ['warning', 'careful', 'caution']):
                    callout_type = 'warning'
                elif any(w in text.lower() for w in ['danger', 'critical', 'never', 'do not']):
                    callout_type = 'danger'
                elif any(w in text.lower() for w in ['insight', 'tip', 'key']):
                    callout_type = 'insight'
                elif any(w in text.lower() for w in ['deep dive', 'advanced']):
                    callout_type = 'deep'

                icons = {'info': '💡', 'warning': '⚠️', 'danger': '🚫', 'insight': '✨', 'deep': '🔬'}
                titles = {'info': 'Note', 'warning': 'Warning', 'danger': 'Important', 'insight': 'Insight', 'deep': 'Deep Dive'}

                # Extract title if present (text before colon or first sentence)
                title_match = re.match(r'^(?:\*\*)?([^:*]+?)(?:\*\*)?:', text)
                if title_match:
                    title = title_match.group(1).strip()
                    body = text[title_match.end():].strip()
                else:
                    title = titles.get(callout_type, 'Note')
                    body = text

                html_parts.append(f'''<div class="callout callout-{callout_type} fade-in">
  <span class="callout-icon">{icons.get(callout_type, '💡')}</span>
  <div class="callout-title">{title}</div>
  <div class="callout-body">{inline_md(body)}</div>
</div>''')
                in_blockquote = False
                blockquote_lines = []
                i += 1
                continue

        # Empty lines
        if not line.strip():
            html_parts.append('')
            i += 1
            continue

        # Horizontal rules
        if line.strip() in ('---', '***', '___'):
            html_parts.append('<hr class="fade-in">')
            i += 1
            continue

        # Headers
        header_match = re.match(r'^(#{1,6})\s+(.+)', line)
        if header_match:
            level = len(header_match.group(1))
            text = header_match.group(2).strip()
            # Add anchor id
            anchor_id = re.sub(r'[^\w\s-]', '', text.lower()).replace(' ', '-')
            if level == 1:
                html_parts.append(f'<h1 id="{anchor_id}" class="article-title fade-in">{inline_md(text)}</h1>')
            elif level == 2:
                html_parts.append(f'<h2 id="{anchor_id}" class="section-title fade-in">{inline_md(text)}</h2>')
            elif level == 3:
                html_parts.append(f'<h3 id="{anchor_id}" class="content-subtitle fade-in">{inline_md(text)}</h3>')
            else:
                html_parts.append(f'<h{level} id="{anchor_id}">{inline_md(text)}</h{level}>')
            i += 1
            continue

        # Unordered lists
        if re.match(r'^[\s]*[-*+]\s', line):
            if not in_list or list_type != 'ul':
                in_list = True
                list_type = 'ul'
                html_parts.append('<ul class="fade-in">')
            content = re.sub(r'^[\s]*[-*+]\s', '', line)
            html_parts.append(f'  <li>{inline_md(content)}</li>')
            # Check if next line is still list
            if i + 1 < len(lines) and re.match(r'^[\s]*[-*+]\s', lines[i + 1]):
                i += 1
                continue
            else:
                html_parts.append('</ul>')
                in_list = False
                list_type = None
                i += 1
                continue

        # Ordered lists
        if re.match(r'^[\s]*\d+\.\s', line):
            if not in_list or list_type != 'ol':
                in_list = True
                list_type = 'ol'
                html_parts.append('<ol class="fade-in">')
            content = re.sub(r'^[\s]*\d+\.\s', '', line)
            html_parts.append(f'  <li>{inline_md(content)}</li>')
            if i + 1 < len(lines) and re.match(r'^[\s]*\d+\.\s', lines[i + 1]):
                i += 1
                continue
            else:
                html_parts.append('</ol>')
                in_list = False
                list_type = None
                i += 1
                continue

        # Regular paragraphs
        if in_list:
            html_parts.append('</ul>' if list_type == 'ul' else '</ol>')
            in_list = False
            list_type = None

        html_parts.append(f'<p class="fade-in">{inline_md(line)}</p>')
        i += 1

    # Close any open tags
    if in_list:
        html_parts.append('</ul>' if list_type == 'ul' else '</ol>')

    return '\n'.join(html_parts)


def inline_md(text):
    """Process inline markdown: bold, italic, code, links."""
    # Inline code (before other processing to avoid conflicts)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    # Bold + italic
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', text)
    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Italic
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    # Links
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    return text


# ─── HTML Template ───

def make_html_page(module_id, meta, content_html, nav_html):
    """Wrap content in a full HTML page."""
    lang_class = f'lang-{meta["lang"]}'
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{meta["title"]} — Agentic Platform Course</title>
  <link rel="stylesheet" href="{CSS_REL}">
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>⚡</text></svg>">
</head>
<body>
  <div class="bg-gradient"></div>
  <div class="particles"></div>
  <div class="reading-progress"></div>

  <nav class="nav">
    <div class="nav-inner">
      <a href="../index.html" class="nav-logo">⚡ Agentic Platform</a>
      {nav_html}
    </div>
  </nav>

  <main class="container">
    <div class="article">
      <div class="article-header fade-in">
        <div class="article-week">{meta["week"]}</div>
        <h1 class="article-title">{meta["title"]}</h1>
        <div class="article-meta">
          <span class="article-meta-item">
            <svg class="article-meta-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            {meta["week"]}
          </span>
          <span class="article-meta-item">
            <svg class="article-meta-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>
            {meta["desc"]}
          </span>
          <span class="article-meta-item {lang_class}" style="font-weight:600;color:var(--accent-{"blue" if meta["lang"]=="go" else "purple" if meta["lang"]=="elixir" else "emerald"})">
            {LANG_LABELS.get(meta["lang"], meta["lang"])}
          </span>
        </div>
      </div>

      <div class="content">
        {content_html}
      </div>

      <div class="module-nav fade-in" style="display:flex;justify-content:space-between;margin-top:4rem;padding-top:2rem;border-top:1px solid var(--border-subtle);">
        {get_prev_link(module_id)}
        {get_next_link(module_id)}
      </div>

      <div class="agnt-badge fade-in">
        <a href="https://github.com/huvaxstra/AGNT" target="_blank" rel="noopener" class="agnt-badge-inner">
          <span class="agnt-badge-icon">A</span>
          <span class="agnt-badge-text">Powered by <strong>AGNT</strong> — Software Factory for the AI Era</span>
        </a>
      </div>
    </div>
  </main>

  <footer class="agnt-footer">
    <p>Built with <a href="https://github.com/huvaxstra/AGNT" target="_blank" rel="noopener">AGNT</a> · Hybrid Elixir/Go Agentic Platform Engineering · 16 Weeks</p>
  </footer>

  <script src="{JS_REL}"></script>
</body>
</html>'''


MODULE_ORDER = [
    '00-setup', '01-go-fundamentals', '02-go-cli-http', '03-elixir-fundamentals',
    '04-otp-genserver', '05-multi-agent-supervision', '06-phoenix-liveview',
    '07-agent-communication', '08-agent-state-durable', '09-advanced-otp',
    '10-clustering-distribution', '11-go-k8s-operators', '12-go-prometheus',
    '13-grpc-bridge', '14-observability-stack', '15-production-deployment', '16-capstone'
]


def get_prev_link(module_id):
    idx = MODULE_ORDER.index(module_id) if module_id in MODULE_ORDER else -1
    if idx > 0:
        prev_id = MODULE_ORDER[idx - 1]
        prev_meta = MODULES[prev_id]
        return f'<a href="{prev_id}.html" class="nav-link" style="display:flex;align-items:center;gap:0.5rem;">← {prev_meta["title"]}</a>'
    return '<span></span>'


def get_next_link(module_id):
    idx = MODULE_ORDER.index(module_id) if module_id in MODULE_ORDER else -1
    if idx < len(MODULE_ORDER) - 1:
        next_id = MODULE_ORDER[idx + 1]
        next_meta = MODULES[next_id]
        return f'<a href="{next_id}.html" class="nav-link" style="display:flex;align-items:center;gap:0.5rem;">{next_meta["title"]} →</a>'
    return '<span></span>'


def make_nav_html(module_id):
    """Generate navigation links for the top bar."""
    idx = MODULE_ORDER.index(module_id) if module_id in MODULE_ORDER else 0
    links = []
    for i, mid in enumerate(MODULE_ORDER):
        if mid in MODULES:
            m = MODULES[mid]
            active = ' active' if mid == module_id else ''
            links.append(f'<a href="{mid}.html" class="nav-link{active}" title="{m["title"]}">{m["week"].replace("Week ", "W")}</a>')
    return '<ul class="nav-links">' + ''.join(links) + '</ul>'


def main():
    HTML_DIR.mkdir(parents=True, exist_ok=True)

    count = 0
    for module_id in MODULE_ORDER:
        meta = MODULES.get(module_id)
        if not meta:
            continue

        md_path = LEARN_DIR / f'{module_id}.md'
        if not md_path.exists():
            print(f'  SKIP: {md_path.name} (not found)')
            continue

        print(f'  Converting: {module_id}.md → {module_id}.html')
        md_text = md_path.read_text(encoding='utf-8')
        content_html = md_to_html(md_text)
        nav_html = make_nav_html(module_id)
        page_html = make_html_page(module_id, meta, content_html, nav_html)

        out_path = HTML_DIR / f'{module_id}.html'
        out_path.write_text(page_html, encoding='utf-8')
        count += 1

    print(f'\nDone! Converted {count} modules to HTML in html/')


if __name__ == '__main__':
    main()
