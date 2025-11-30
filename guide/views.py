import os
import re

from django.conf import settings
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse


def get_docs_path():
    return os.path.join(settings.BASE_DIR, 'docs')

def convert_guide_urls(content):
    """Convert Django URL patterns (guide:index, guide:detail) to actual URLs in markdown content"""
    # Convert guide:index
    index_url = reverse('guide:index')
    content = re.sub(
        r'\[([^\]]+)\]\(guide:index\)',
        f'[\\1]({index_url})',
        content
    )

    # Convert guide:detail doc_name
    def replace_detail(match):
        link_text = match.group(1)
        doc_name = match.group(2).strip()
        detail_url = reverse('guide:detail', kwargs={'doc_name': doc_name})
        return f'[{link_text}]({detail_url})'

    content = re.sub(
        r'\[([^\]]+)\]\(guide:detail\s+([^)]+)\)',
        replace_detail,
        content
    )

    return content

def index(request):
    docs_path = get_docs_path()
    files = []
    if os.path.exists(docs_path):
        for f in sorted(os.listdir(docs_path)):
            if f.endswith('.md'):
                files.append(f)
    return render(request, 'guide/index.html', {'files': files})

def detail(request, doc_name):
    docs_path = get_docs_path()
    file_path = os.path.join(docs_path, doc_name)

    # Security check to prevent directory traversal
    if '..' in doc_name or '/' in doc_name or '\\' in doc_name:
        raise Http404("Invalid document name")

    if not os.path.exists(file_path):
        raise Http404("Document not found")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Convert Django URL patterns to actual URLs
        content = convert_guide_urls(content)
    except Exception as e:
        content = f"Error reading file: {e}"

    return render(request, 'guide/detail.html', {'content': content, 'title': doc_name})
