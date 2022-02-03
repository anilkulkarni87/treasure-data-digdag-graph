import argparse
import logging
import os
import time
from uuid import uuid4
import json

import yaml
from graphviz import Digraph
import glob
from pathlib import Path

logger = logging.getLogger(__name__)


class Block:
    def __init__(self, graph_name, label, color, penwidth=1.0, href=""):
        self.graph_name = graph_name
        self.name = str(uuid4())
        self.label = label
        self.color = color
        self.penwidth = penwidth
        self.href = href

        self.subblocks = []
        self.subgraph_name = "cluster-" + str(uuid4())

        self.parallel = False

    def append(self, label, color="", penwidth=1.0):
        block = Block(self.subgraph_name, label, self.color, self.penwidth, self.href)
        self.subblocks.append(block)
        return block

    def last(self):
        if self.subblocks:
            if self.parallel:
                res = []
                for block in self.subblocks:
                    res += block.last()
                return res
            else:
                return self.subblocks[-1].last()
        return [self]

    def draw(self, dot):
        dot.node(self.name, self.label, color=self.color, penwidth=str(self.penwidth), shape="box", href=self.href)
        #penwidth = str(self.penwidth)
        prev = [self]
        with dot.subgraph(name=self.subgraph_name) as c:
            for block in self.subblocks:
                block.draw(c)
                for b in prev:
                    dot.edge(b.name, block.name)
                if not self.parallel:
                    prev = block.last()


def load(root, data, filepath):
    root.penwidth="1.0"
    dirpath = "/".join(filepath.split("/")[:-1]) + "/"

    for key in data.keys():
        #print(f'{key} --> {data.get(key)}')
        if key == "timezone":
            root.color = "mediumspringgreen"
            block = root.append(data[key])
        if key == "schedule":
            root.color = "magenta1"
            block = root.append(json.dumps(data[key]))
        if key == "_parallel":
            root.color = "purple2"
            root.parallel = data[key]
        if key == "td>":
            root.color = "blue"
            root.label = str(root.label) + "\n" + str(data[key])
        if key == "echo>":
            root.color = "orangered"
        if key == "http>":
            root.color = "darkgreen"
            root.label = str(root.label) + "\n" + str(data[key])
        if key == "mail>":
            root.color = "crimson"
            root.label = str(root.label) + "\n" + str(data[key])
        if key == "if>":
            root.color = "darkorchid2"
            root.label = str(root.label) + "\n" + "if " + str(data[key])
        if key == "call>" or key == "require>":  # or key == "require>":
            fpath = dirpath + data[key]
            root.penwidth = 3.0
            if not fpath.endswith(".dig"):
                fpath += ".dig"
                root.label = str(root.label) + "\n" + str(data[key]) + ".dig"
                root.href = "./" + str(data[key]) + ".html"
            if not os.path.exists(fpath + ".dig"):
                for path in Path(fpath).parent.parent.rglob(f'{data[key]}.dig'):
                    root.href = "../" + path.parent.name + "/" + str(data[key]) + ".html"
            else:
                logger.warning(fpath + " does not exist")
        if key in ["_do", "_error"]:
            block = root.append(key)
            load(block, data[key], filepath)
        if not key.startswith("+"):
            continue
        root.color = "firebrick1"
        root.penwidth="3.0"
        block = root.append(key)
        load(block, data[key], filepath)


def include_constructor(loader: yaml.SafeLoader, node: yaml.nodes.ScalarNode) -> str:
    """Construct a greeting."""
    return f"include {loader.construct_scalar(node)}"


def generate_graph(input_filepath, output_dot_file):
    #filepath = os.getcwd() + "/" + input_filepath
    filepath = input_filepath
    dot = Digraph(format="svg", edge_attr={"color": "red"})
    dot2 = Digraph(format="cmapx", edge_attr={"color": "red"})
    root = Block("root", "Click to HomePage", "brown", href="../../index.html")

    with open(filepath) as f:
        yaml.add_constructor("!include", include_constructor)
        data = yaml.load(f, Loader=yaml.FullLoader)
        load(root, data, filepath)

    root.draw(dot)
    root.draw(dot2)
    dot.render(output_dot_file)
    dot2.render(output_dot_file)
    with open(output_dot_file + '.cmapx', 'r') as cmapx, open(output_dot_file + '.html', 'w') as fp:
        fp.write(f"<IMG SRC=\"{output_dot_file.split('/')[-1]}.svg\" USEMAP=\"#%3\" />")
        fp.writelines(l for l in cmapx)
        pass
    fp.close()
    with open("index.html", 'a', buffering=1) as html:
        relativePath = str(Path(output_dot_file).relative_to(Path(filepath).parent.parent))
        html.write(f"<A href=\"./{relativePath}.html\">{Path(output_dot_file).name} </A><BR>")
        pass
    html.close()


def main():
    count = 0
    for path in Path(os.getcwd()).rglob('*.dig'):
        if "config" not in str(path):
            input_file_path = path
            output_dot_file = f"{os.getcwd()}/graphs/{path.parent.name}/{path.name.replace('.dig','')}"
            # print(f"Input file path: {input_file_path}")
            # print(f"Output file path: {output_dot_file}")
            # print(Path(output_dot_file).relative_to(input_file_path.parent.parent))
            generate_graph(input_filepath=str(input_file_path), output_dot_file=str(output_dot_file))
            count = count + 1
            print(f'Completed generating graph for {input_file_path}')
    print(f'Graphs generated: {count}')

if __name__ == "__main__":
    main()
