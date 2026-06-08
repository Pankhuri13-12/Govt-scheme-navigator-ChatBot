import os

data_dir = "data"
files = [f for f in os.listdir(data_dir) if f.endswith(".txt")]

print(f"Total files: {len(files)}")
print("=" * 50)

# Check file sizes
sizes = []
empty = []
for f in files:
    path = os.path.join(data_dir, f)
    with open(path, encoding="utf-8") as fp:
        content = fp.read().strip()
    sizes.append((f, len(content)))
    if len(content) < 100:
        empty.append(f)

# Sort by size
sizes.sort(key=lambda x: x[1])

print(f"\n── Smallest 5 files:")
for name, size in sizes[:5]:
    print(f"  {size:6} chars — {name}")

print(f"\n── Largest 5 files:")
for name, size in sizes[-5:]:
    print(f"  {size:6} chars — {name}")

avg = sum(s for _, s in sizes) // len(sizes)
print(f"\n── Average file size: {avg} chars")
print(f"── Files under 100 chars (empty): {len(empty)}")
if empty:
    for e in empty:
        print(f"   {e}")

print("\n" + "=" * 50)
print("── Sample content from scheme_0000:")
first = sorted(files)[0]
with open(os.path.join(data_dir, first), encoding="utf-8") as f:
    print(f.read()[:800])