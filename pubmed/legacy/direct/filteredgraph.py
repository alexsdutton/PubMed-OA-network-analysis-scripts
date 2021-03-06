#!/usr/bin/env python

import networkx as nx

import os, sys

import re

from graphml import read_graphml, write_graphml

from collections import defaultdict

from operator import itemgetter

# {cmd} journal regex 

assert len(sys.argv) == 3

_, journal, regex = sys.argv

assert os.path.isfile(journal+".gml")

print "Compiling regex: %s" % regex
p = re.compile(regex, re.U)

print "Loading GraphML network graph for %s" % journal
g = read_graphml(journal+".gml")

print "Creating a directional graph to hold just the citation chains"
filtered_g = nx.DiGraph()
filtered_g.level = {}
filtered_g.position = {}
filtered_g.year = {}

rows = {}

# unescape '_' in the Journal

journal = " ".join(journal.split("_"))

print "Scanning nodes for title regex matches"
hits = set()
for node in g.nodes(data=True):
  if node[1].get('source', '') == journal and node[1].get('_xml_container', '') == '':
    m = p.search(node[1].get('title','') or '')
    if m != None:
      hits.add(node[0])
      filtered_g.level[node[0]] = 1
      filtered_g.add_node(node[0], **node[1])
      filtered_g.year[node[0]] = node[1].get('year', 1990)

rows[0] = hits

print "Found %s works within %s for regex:'%s'" % (len(hits), journal, regex)

def get_children(g, nodes, filtered_g, level):
  children = {}
  # got seed ids
  for uid in hits:
    cites = g.successors(uid)
    if cites:
      for item in cites:
        if g.node[item].get('source','') == journal:
          if not children.has_key(uid):
            children[uid] = []
          children[uid].append(item)
          filtered_g.add_node(item, **g.node[item])
          filtered_g.add_edge(uid, item)
          filtered_g.level[item] = level+1
          filtered_g.year[item] = g.node[item].get('year', 1990)
  rows[level] = set(children.keys())
  return children

level = 1
while(hits):
  print "Getting cited works at level %s" % level
  children_dict = get_children(g, hits, filtered_g, level)
  hits = set()
  if children_dict:
    for l in children_dict.values():
      hits.update(l)
    print "Found %s cited works within %s by %s articles at level %s" % (len(hits), journal, len(children_dict.keys()), level)
    level = level + 1

years = [filtered_g.node[i].get('year',1930) for i in filtered_g.nodes()]

try:
  year_max = int(max(years)[:4])
except ValueError:
  print "Couldn't convert the max year '%s' to an int" % years
try:
  year_min = int(min(years)[:4])
except ValueError:
  print "Couldn't convert the max year '%s' to an int" % year_max

print year_max, year_min

dx = (year_max - year_min)/900.0

offset = defaultdict(lambda: defaultdict(lambda: 0))

print "2nd pass - removing any nodes with degree == 0"

for node in filtered_g.nodes():
  # set position
  if filtered_g.degree(node) == 0:
    filtered_g.remove_node(node)
    for row in rows:
      if node in rows[row]:
        pass
        rows[row].remove(node)

for node in filtered_g.nodes():
  try:
    thisy = int(filtered_g.year[node][:4])
    if filtered_g.node[i].get('month',''):
      try:
        month = int(filtered_g.node[node].get('month',''))
        if month > 1:
          thisy = thisy + ((month-1.0)/12.0)
      except ValueError:
        pass
    thisl = filtered_g.level[node]
    filtered_g.position[node] = (dx * (thisy - year_min), 900 - 100 * thisl - offset[thisl][thisy])
    offset[thisl][thisy] = offset[thisl][thisy] + 8
  except ValueError:
    print "Couldn't set position based on year for %s" % node
    print "Using x -> 0 instead"
    filtered_g.position[node] = (0 , 900 - 100 * filtered_g.level[node])

for year_marker in xrange(year_max+1-year_min):
  filtered_g.add_node(year_marker+year_min)
  filtered_g.position[year_marker+year_min] = (dx * year_marker, 950)

# Most cited
degrees = [(x, len(filtered_g.predecessors(x))) for x in filtered_g.nodes()]
top5 = sorted(degrees, key=itemgetter(1), reverse=True)[:5]
print "Top cited works:"
for item, citers in top5:
  print "%s - %s.  Cited %s times" % (item, filtered_g.node[item].get('title',''), citers)
  
# Most same-journal citations
degrees = [(x, len(filtered_g.successors(x))) for x in filtered_g.nodes()]
top5 = sorted(degrees, key=itemgetter(1), reverse=True)[:5]
print "Top same-journal citations:"
for item, citers in top5:
  print "%s - %s.  Citing a %s-sourced article %s times" % (item, filtered_g.node[item].get('title',''), journal, citers)
  
print "Writing out GraphML graph to %s" % (journal+"-"+regex+".gml")
write_graphml(filtered_g, open(journal+"-"+regex+".gml", "w"))

print "Attempting to draw graph for viewing"
import matplotlib.pyplot as plt
plt.figure(figsize=(8,8))
#nx.draw(filtered_g, node_colors=[float(filtered_g.level[x] % 4 *64) for x in filtered_g])
nx.draw(filtered_g, filtered_g.position, node_size=50, node_color=[float(filtered_g.degree(v)*4) for v in filtered_g])
print "Saving graph image as %s" % (journal+"-"+regex+".png")
plt.savefig(journal+"-"+regex+".png")
plt.show()
