import argparse
import logging
import os
from uuid import uuid4
import json

import yaml
from graphviz import Digraph
import glob

logger = logging.getLogger(__name__)


class Block:
    def __init__(self, graph_name, label, color, penwidth=1.0):
        self.graph_name = graph_name
        self.name = str(uuid4())
        self.label = label
        self.color = color
        self.penwidth = penwidth

        self.subblocks = []
        self.subgraph_name = "cluster-" + str(uuid4())

        self.parallel = False

    def append(self, label, color="", penwidth=1.0):
        block = Block(self.subgraph_name, label, self.color, self.penwidth)
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
        dot.node(self.name, self.label, color=self.color, penwidth=str(self.penwidth), shape="box")
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
            if os.path.exists(fpath):
                with open(fpath) as f:
                    data = yaml.load(f, Loader=yaml.FullLoader)
                    load(root, data, fpath)
                    continue
            else:
                logger.warning(fpath + " does not exist")
        if key in ["_do", "_error"]:
            block = root.append(key)
            load(block, data[key], filepath)
        if not key.startswith("+"):
            #print(f'{key} --> {data.get(key)}')
            continue
        #print(f'{key} --> {data.get(key)}')
        root.color = "firebrick1"
        root.penwidth="3.0"
        block = root.append(key)
        load(block, data[key], filepath)


def include_constructor(loader: yaml.SafeLoader, node: yaml.nodes.ScalarNode) -> str:
    """Construct a greeting."""
    return f"include {loader.construct_scalar(node)}"


def generate_graph(input_filepath, output_dot_file):
    filepath = os.getcwd() + "/" + input_filepath
    dot = Digraph(format="png", edge_attr={"color" : "red"})
    root = Block("root", "root", "brown")

    with open(filepath) as f:
        yaml.add_constructor("!include", include_constructor)
        data = yaml.load(f, Loader=yaml.FullLoader)
        load(root, data, filepath)

    root.draw(dot)
    dot.render(output_dot_file)


def main():
    dir_name = 'project1/'
    input_filepath_list = glob.glob(dir_name + "*.dig")
    for input_file_path in input_filepath_list:
        output_dot_file = "graphs/" + dir_name + (input_file_path.split("/")[1]).split(".")[0]
        generate_graph(input_filepath=input_file_path, output_dot_file=output_dot_file)
        print(f'Completed generating graph for {input_file_path}')


if __name__ == "__main__":
    main()
