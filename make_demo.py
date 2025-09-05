import collections
import csv
import dataclasses
import enum
import functools
from pathlib import Path
from typing import Tuple


class Quality(enum.Enum):
  """Quality of the font."""

  UNKNOWN = 0
  LOW = 1
  MEDIUM = 2
  HIGH = 3


@dataclasses.dataclass(frozen=True)
class Tag:
	family: str
	name: str
	location: str
	weight: float


def tags_for(family: str) -> tuple[Tag, ...]:
  """Returns the tags for the font."""
  return tuple(
      t
      for t in tags()
      if t.family == family
  )


def quality_tags_for(family: str) -> tuple[Tag, ...]:
	return quality_tags_by_family().get(family, tuple())


def min_quality_for(family: str) -> float:
	return min(t.weight for t in quality_tags_for(family))


def quality_for(family: str) -> Quality:
  """Returns the quality of the font."""
  quality_tags = quality_tags_for(family)
  if not quality_tags:
    return Quality.UNKNOWN
  min_quality = min_quality_for(family)

  # If the font has a quality tag other than wordspace and the wordspace is at
  # least 90, then the font is high quality.
  if (
      any(t for t in quality_tags if t.name != '/Quality/Wordspace')
      and min_quality >= 90
  ):
    return Quality.HIGH
  elif min_quality <= 25:
    return Quality.LOW
  return Quality.MEDIUM


@functools.cache
def gf_dir() -> Path:
	gf_dir = Path(__file__).parent.parent / "fonts"
	assert gf_dir.is_dir()
	return gf_dir


@functools.cache
def quality_tags_by_family() -> dict[str, Tuple[Tag, ...]]:
	by_family = collections.defaultdict(tuple)
	for t in tags():
		if not t.name.startswith("/Quality/"):
			continue
		by_family[t.family] += (t,)
	return by_family



@functools.cache
def tags() -> Tuple[Tag, ...]:
	tag_files = (gf_dir() / "tags" / "all").rglob("*.csv")
	tags = set()
	for tag_file in tag_files:
		if tag_file.name == "families_new.csv":
			continue
		with open(tag_file) as f:
			rdr = csv.reader(f)
			rows = tuple(r for r in rdr)
		for row in rows:
			row[-1] = float(row[-1])
			if len(row) == 3:
				tag = Tag(row[0], row[1], None, row[2])
			elif len(row) == 4:
				tag = Tag(*row)
			else:
				raise ValueError("Bad line " + row)
			tags.add(tag)
	return tags


def css_url(families):
	css_families = "&".join("family=" + f.replace(" ", "+") for f in families)
	return f"@import url(https://fonts.googleapis.com/css2?{css_families});"


def main():
	families = sorted(
		{t.family for t in tags() if quality_for(t.family) != Quality.UNKNOWN},
		key=lambda f: (-quality_for(f).value, -min_quality_for(f), f)
	)
	print("<!DOCTYPE html>")
	print("<html>")
	print("<style>")
	pending_families = []
	for family in families:
		pending_families.append(family.replace(" ", "+"))
		if sum(len(f) for f in pending_families) > 256:
			print(css_url(pending_families))
			pending_families = []
	if pending_families:
		print(css_url(pending_families))
		pending_families = []
	
	print("</style>")
	print("<body>")
	print("<pre>Dump families by quality group and lowest quality score</pre>")
	print("<pre>Meant to help judge whether our High/Medium/Low thresholds are good</pre>")
	print("<pre>Notably, it is likely some users will filter to only items in Quality.HIGH</pre>")
	print("<pre>Produced by https://github.com/rsheeter/quality_threshold</pre>")
	current_group = None
	current_quality = 101.0  # so the first family prints a quality
	for family in families:
		family_group = quality_for(family)
		if family_group != current_group:
			current_group = family_group
			print(f"  <h2 style=\"color: blue\">{family_group}</h2>")
		family_quality = min_quality_for(family)
		if family_quality < current_quality:
			print(f"  <h3 style=\"color: purple\">==min quality {family_quality}==</h3>")
			current_quality = family_quality
		print(f"  <div style=\"font-family: '{family}';\">")
		print(f"    {family}")
		print("  </div>")
	print("</body>")
	print("</html>")

if __name__ == "__main__":
	main()