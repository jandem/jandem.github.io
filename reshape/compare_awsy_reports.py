from collections import defaultdict
from operator import itemgetter
import json

before = ["/Users/jandem/Downloads/awsy-before1",
    "/Users/jandem/Downloads/awsy-before2",
    "/Users/jandem/Downloads/awsy-before3"]
after = ["/Users/jandem/Downloads/awsy-after1",
    "/Users/jandem/Downloads/awsy-after2",
    "/Users/jandem/Downloads/awsy-after3"]

def sizeof_fmt(num, suffix='B'):
    for unit in ['','K','M','G','T','P','E','Z']:
        if abs(num) < 1024.0:
            return "%3.2f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.2f%s%s" % (num, 'Yi', suffix)

class Node(object):
    def __init__(self):
        self.name = ""
        self.amount = 0
        self.children = defaultdict(lambda: Node())
        self.collapsed = False
        self.color = None
    
    def calculate(self):
        if len(self.children) > 0:
            assert self.amount == 0
            for child in self.children.values():
                self.amount += child.calculate()
        return self.amount

    def set_color(self, color, incl_children):
        self.color = color
        if incl_children:
            for child in self.children.values():
                child.set_color(color, incl_children)

    def collapse(self):
        self.children = {}
        self.collapsed = True

    def write(self, output, level=0):
        if len(self.name) == 0:
            return
        output.write("  " * level)
        if self.color:
            output.write("<span style=\"font-weight: bold; color: " + self.color + "\">")
        output.write(self.name + ": " + sizeof_fmt(self.amount) + "<br>")
        if self.color:
            output.write("</span>")
        names = sorted(self.children, key=lambda v: self.children[v].amount, reverse=True)
        for name in names:
            self.children[name].write(output, level + 1)

def add_to_tree(trees, process, path, amount):
    parts = path.split("/")
    process = process.split(" ")[0]
    processes.add(process)
    node = trees[process]
    for i in range(len(parts)):
        part = parts[i]
        node = node.children[part]
        if i == len(parts) - 1:
            node.amount = amount
        node.name = part

def process_file(path):
    with open(path) as f:
        data = json.load(f)
        reports = data["reports"]

    trees = defaultdict(lambda: Node())
    for report in reports:
        add_to_tree(trees, report["process"], report["path"], report["amount"])
    return trees

def write_tree(output, tree):
    tree.calculate()
    js_node = tree.children["js-main-runtime"]
    js_node.children["realms"].collapse()
    for name, node in js_node.children["zones"].children.items():
        if not name in ["shapes", "property-maps"]:
            node.collapse()

    js_node.set_color("black", False)
    js_node.children["zones"].children["shapes"].set_color("red", True)
    js_node.children["zones"].children["property-maps"].set_color("blue", True)
    js_node.children["zones"].children["shape-tables"].set_color("darkgreen", True)

    js_node.write(output)

def write_diff(output, label, color, before_amount, after_amount):
    diff = after_amount - before_amount
    if before_amount != 0:
        diff_percent = diff / float(before_amount)
    else:
        diff_percent = 0
    output.write("<span style=\"font-weight: bold; color: " + color + "\">")
    output.write(label + ": ")
    output.write(("+" if diff >= 0 else "") + sizeof_fmt(diff))
    if before_amount != 0 and after_amount != 0:
        output.write(" ({:.2%})".format(diff_percent))
    output.write("</span><br>")

processes = set()

before_results = []
after_results = []

assert len(before) == len(after)

for path in before:
    before_results.append(process_file(path))

for path in after:
    after_results.append(process_file(path))

output = open("/tmp/output.htm", "w")

output.write("""
<style type="text/css">
body {
    font-family: sans-serif;
}
table td {
    vertical-align: top;
    font-size: .92em;
}
</style>
""")

for p in sorted(processes):
    output.write("<h2>Process: " + p + "</h2>")

    for i in range(len(before_results)):
        before = before_results[i][p]
        after = after_results[i][p]

        if "js-main-runtime" not in before.children:
            continue

        js_before = before.children["js-main-runtime"]
        js_after = after.children["js-main-runtime"]

        output.write("<table>")
        output.write("<tr><th>Before</th><th>After</th><th>Difference</th></tr>")

        output.write("<tr>")
        
        output.write("<td><pre>")
        write_tree(output, before)
        output.write("<pre></td>")
        
        output.write("<td><pre>")
        write_tree(output, after)
        output.write("</pre></td>")

        output.write("<td><pre>")

        write_diff(output, "js-main-runtime", "black", js_before.amount, js_after.amount)

        before_amount = js_before.children["zones"].children["shapes"].amount
        after_amount = js_after.children["zones"].children["shapes"].amount
        write_diff(output, "shapes", "red", before_amount, after_amount)

        before_amount = js_before.children["zones"].children["property-maps"].amount
        after_amount = js_after.children["zones"].children["property-maps"].amount
        write_diff(output, "property-maps", "blue", before_amount, after_amount)

        before_amount = js_before.children["zones"].children["shape-tables"].amount
        after_amount = js_after.children["zones"].children["shape-tables"].amount
        write_diff(output, "shape-tables", "darkgreen", before_amount, after_amount)

        output.write("</pre></td>")

        output.write("</tr>")
        output.write("</table>")

"""
"""
output.close()
