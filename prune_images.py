import re
import pathlib
import urllib.parse

root = pathlib.Path('.')

# Collect referenced local paths from HTML/CSS/JS/XML
url_pat = re.compile(r'''(?ix)
(?:src|href)\s*=\s*['"]([^'"]+)['"]
|url\(\s*['"]?([^'")]+)['"]?\s*\)
''')

def normalize(u: str):
    u = (u or '').strip()
    if not u:
        return None
    if u.startswith(('mailto:', 'tel:', 'javascript:', '#')):
        return None
    u = u.split('#', 1)[0].split('?', 1)[0]
    u = urllib.parse.unquote(u)
    # drop scheme+host
    if u.startswith(('http://', 'https://')):
        p = urllib.parse.urlparse(u)
        u = p.path.lstrip('/')
    u = u.lstrip('/')
    # collapse ./
    while u.startswith('./'):
        u = u[2:]
    return u

refs = set()
for p in root.rglob('*'):
    if p.suffix.lower() in {'.html', '.css', '.js', '.xml'}:
        txt = p.read_text('utf-8', errors='ignore')
        for m in url_pat.finditer(txt):
            u = m.group(1) or m.group(2)
            u = normalize(u)
            if not u:
                continue
            if u.startswith('wp-content/uploads/'):
                refs.add(u)

# Some generators might reference only the original image but the page could use responsive srcset.
# Our static export currently doesn't include srcset, so we keep only what is explicitly referenced.

# Build list of all image files under uploads
uploads_dir = root / 'wp-content' / 'uploads'
img_exts = {'.png', '.jpg', '.jpeg', '.webp', '.svg', '.ico', '.avif', '.gif'}
all_imgs = []
if uploads_dir.exists():
    for p in uploads_dir.rglob('*'):
        if p.is_file() and p.suffix.lower() in img_exts:
            all_imgs.append(p)

keep_paths = {str(root / r) for r in refs}
keep = []
remove = []
for p in all_imgs:
    if str(p) in keep_paths:
        keep.append(p)
    else:
        remove.append(p)

bytes_all = sum(p.stat().st_size for p in all_imgs)
bytes_remove = sum(p.stat().st_size for p in remove)

print(f"Referenced uploads: {len(refs)}")
for r in sorted(refs):
    print(f"- {r}")
print(f"All image files under uploads: {len(all_imgs)}")
print(f"Will remove: {len(remove)}")
print(f"Image bytes total: {bytes_all}")
print(f"Image bytes to remove: {bytes_remove}")

for p in remove:
    p.unlink()

# Remove empty directories
for d in sorted([p for p in uploads_dir.rglob('*') if p.is_dir()], key=lambda x: len(str(x)), reverse=True):
    try:
        next(d.iterdir())
    except StopIteration:
        d.rmdir()

print("Done")
