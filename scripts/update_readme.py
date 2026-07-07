import os
import re
import requests
from datetime import datetime, timezone

TOKEN = os.environ['GITHUB_TOKEN']
USERNAME = '365diascollaboration-prog'

HEADERS = {
    'Authorization': f'token {TOKEN}',
    'Accept': 'application/vnd.github.v3+json'
}

LANG_ICON = {
    'Python': '🐍',
    'JavaScript': '⚡',
    'TypeScript': '💙',
    'HTML': '🌐',
    'CSS': '🎨',
    'Shell': '🔧',
    'Dockerfile': '🐳',
}


def get_repos():
    repos, page = [], 1
    while True:
        r = requests.get(
            f'https://api.github.com/users/{USERNAME}/repos',
            headers=HEADERS,
            params={'per_page': 100, 'page': page, 'sort': 'updated', 'type': 'owner'}
        )
        batch = r.json()
        if not batch:
            break
        repos.extend(batch)
        page += 1
    return [r for r in repos if not r['fork'] and r['name'] != USERNAME]


def get_collaborations():
    r = requests.get(
        'https://api.github.com/search/issues',
        headers=HEADERS,
        params={
            'q': f'author:{USERNAME} type:pr is:merged -user:{USERNAME}',
            'sort': 'updated',
            'per_page': 10
        }
    )
    data = r.json()
    return data.get('items', []), data.get('total_count', 0)


def build_repos_table(repos):
    rows = [
        '| Proyecto | Stack | ⭐ | Descripción |',
        '|----------|-------|----|-------------|',
    ]
    for repo in repos[:8]:
        name = repo['name']
        url = repo['html_url']
        desc = (repo.get('description') or '—')[:60]
        lang = repo.get('language')
        stars = repo.get('stargazers_count', 0)
        icon = LANG_ICON.get(lang, '📦')
        lang_str = f'{icon} {lang}' if lang else '📦 —'
        rows.append(f'| **[{name}]({url})** | `{lang_str}` | {stars} | {desc} |')
    return '\n'.join(rows)


def get_repo_stars(repo_name):
    r = requests.get(f'https://api.github.com/repos/{repo_name}', headers=HEADERS)
    return r.json().get('stargazers_count', 0)


def fmt_stars(n):
    return f'{n / 1000:.1f}K'.replace('.0K', 'K') if n >= 1000 else str(n)


def build_collabs_table(items):
    if not items:
        return '_Sin colaboraciones externas mergeadas aún._'
    rows = [
        '| Repositorio Externo | ⭐ | Pull Request | Merged |',
        '|---------------------|----|--------------|--------|',
    ]
    for item in items[:8]:
        pr_title = item['title'][:55]
        pr_url = item['html_url']
        repo_name = item['repository_url'].replace('https://api.github.com/repos/', '')
        repo_url = f'https://github.com/{repo_name}'
        stars = fmt_stars(get_repo_stars(repo_name))
        merged = (item.get('closed_at') or '—')[:10]
        rows.append(f'| **[{repo_name}]({repo_url})** | {stars} | [{pr_title}]({pr_url}) | `{merged}` |')
    return '\n'.join(rows)


def inject(content, marker, block):
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    replacement = (
        f'<!-- {marker}-START -->\n'
        f'{block}\n\n'
        f'<sub>🤖 Auto-actualizado: {now}</sub>\n'
        f'<!-- {marker}-END -->'
    )
    return re.sub(
        rf'<!-- {marker}-START -->.*?<!-- {marker}-END -->',
        replacement,
        content,
        flags=re.DOTALL
    )


if __name__ == '__main__':
    print('→ Obteniendo repos propios...')
    repos = get_repos()
    print(f'  {len(repos)} repos encontrados')

    print('→ Obteniendo colaboraciones externas...')
    collabs, pr_total = get_collaborations()
    print(f'  {pr_total} PRs mergeados en repos externos')

    with open('README.md', 'r', encoding='utf-8') as f:
        content = f.read()

    content = inject(content, 'REPOS', build_repos_table(repos))
    content = inject(content, 'COLLAB', build_collabs_table(collabs))
    badge = f'https://img.shields.io/badge/🦈_PRs_mergeados_open_source-{pr_total}-7c3aed?style=for-the-badge'
    content = re.sub(
        r'<!-- PRBADGE-START -->.*?<!-- PRBADGE-END -->',
        f'<!-- PRBADGE-START -->[![PRs mergeados]({badge})](#-colaboraciones)<!-- PRBADGE-END -->',
        content,
        flags=re.DOTALL
    )

    with open('README.md', 'w', encoding='utf-8') as f:
        f.write(content)

    print('✓ README actualizado.')
