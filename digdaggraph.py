!pip install cron-descriptor

import logging
import html
import json
import logging
import os
import time
from pathlib import Path
from uuid import uuid4

import yaml
from cron_descriptor import get_description
from graphviz import Digraph

html.escape = lambda *args, **kwargs: args[0]
from prettytable import PrettyTable

logger = logging.getLogger(__name__)


class Block:
    def __init__(self, graph_name, label, color, penwidth=1.0, href="", shape="box", tooltip=""):
        self.graph_name = graph_name
        self.name = str(uuid4())
        self.label = label
        self.color = color
        self.penwidth = penwidth
        self.href = href
        self.shape = shape
        self.tooltip = tooltip

        self.subblocks = []
        self.subgraph_name = "cluster-" + str(uuid4())

        self.parallel = False

    def append(self, label, color="", penwidth=1.0, shape="box", href="", tooltip=""):
        block = Block(self.subgraph_name, label, color=color, penwidth=penwidth, href=href, shape=shape,
                      tooltip=tooltip)
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
        dot.node(self.name, self.label, color=self.color, penwidth=str(self.penwidth), shape=self.shape, href=self.href,
                 tooltip=self.tooltip)
        prev = [self]
        with dot.subgraph(name=self.subgraph_name) as c:
            for block in self.subblocks:
                block.draw(c)
                for b in prev:
                    dot.edge(b.name, block.name)
                if not self.parallel:
                    prev = block.last()

pt = PrettyTable()
pt.border = True
pt.format = False
pt.field_names= ["Workflow Name", "Schedule", "Link to workflow"]

def load(root, data, filepath):
    root.penwidth = "1.0"
    root.href = ""
    dirpath = "/".join(filepath.split("/")[:-1]) + "/"
    if data is None:
        data = {'Empty Task': 'This is empty dummy task'}
    for key in data.keys():
        logger.info(f'{key} --> {data.get(key)}')
        if key == "timezone":
            block = root.append(data[key], color="mediumspringgreen", shape="cds")
        if key == "schedule":
            table_format = []
            workflow =get_workflow_name_from_filepath(filepath)
            schedule=""
            if "cron>" in data[key]:
                label = json.dumps(data[key]) + "\n" + get_description(data[key]["cron>"])
                schedule=label
                block = root.append(label=label,
                                    color="magenta1", href="", shape="component")
            else:
                label = str(key) + "\n" + json.dumps(data[key])
                schedule = label
                block = root.append(label=label, color="magenta1", href="", shape="component")
            table_format.append([workflow,schedule])
            pt.add_row([workflow,schedule, get_workflow_link_from_filepath(filepath)])

        if key == "_export":
            label = str(key) + "\n" + json.dumps(data[key]).replace(",","\n")
            block = root.append(label=label,
                                color="goldenrod4", href="", shape="box3d", penwidth="2.0")
        if key == "_parallel":
            root.color = "purple2"
            root.parallel = data[key]
        if key == "td>":
            root.color = "webgreen"
            root.label = str(root.label) + "\n" + str(data[key])
            root.penwidth = "1.5"
            if "queries/" in str(data[key]):
                root.tooltip = get_query_file_content(filepath, str(data[key]))
            else:
                root.tooltip = str(data[key])
        if key == "echo>":
            root.color = "lightslategray"
            root.label = str(root.label) + "\n" + str(data)
            root.penwidth = "1.9"
        if key == "http>":
            root.color = "darkgreen"
            root.label = str(root.label) + "\n" + str(data[key])
        if key == "mail>":
            root.color = "crimson"
            root.label = str(root.label) + "\n" + str(data[key])
        if key == "if>":
            root.color = "darkorchid2"
            root.label = str(root.label) + "\n" + "if " + str(data[key])
            root.shape = "diamond"
        if key == "call>" or key == "require>":
            fpath = dirpath + data[key]
            root.color = "cornflowerblue"
            root.penwidth = "3.0"
            if not fpath.endswith(".dig"):
                fpath += ".dig"
                root.label = str(root.label) + "\n" + str(data[key]) + ".dig"
                root.href = "./" + str(data[key]) + ".html"
            if not os.path.exists(fpath + ".dig"):
                for path in Path(fpath).parent.parent.rglob(f'{data[key]}.dig'):
                    root.href = "../" + path.parent.name + "/" + str(data[key]) + ".html"
            else:
                logger.warning(fpath + " does not exist")
        if key in ["_do"]:
            block = root.append(key, penwidth="1.0", color="green", shape="note")
            load(block, data[key], filepath)
        if key in ["_error"]:
            block = root.append(key, penwidth="1.0", color="red", shape="Mcircle")
            load(block, data[key], filepath)
        if not key.startswith("+"):
            continue
        if root.label == "Click to HomePage":
            root.href = "../../index.html"
        block = root.append(key)
        load(block, data[key], filepath)


def include_constructor(loader: yaml.SafeLoader, node: yaml.nodes.ScalarNode) -> str:
    """Construct a greeting."""
    return f"include {loader.construct_scalar(node)}"


def generate_graph(input_filepath, output_dot_file):
    filepath = input_filepath
    dot = Digraph(format="svg", edge_attr={"color": "red"})
    dot2 = Digraph(format="cmapx", edge_attr={"color": "red"})
    root = Block("root", "Click to HomePage", "brown")

    with open(filepath) as f:
        yaml.add_constructor("!include", include_constructor)
        data = yaml.load(f, Loader=yaml.FullLoader)
        load(root, data, filepath)

    root.draw(dot)
    root.draw(dot2)
    dot.render(output_dot_file)
    logger.info("dot.render(output_dot_file)")
    cmapx_file = dot2.render(output_dot_file)
    with open(output_dot_file + '.cmapx', 'r') as cmapx, open(output_dot_file + '.html', 'w') as fp:
        fp.write(f"<IMG SRC=\"{output_dot_file.split('/')[-1]}.svg\" USEMAP=\"#%3\"/>")
        fp.writelines(l for l in cmapx)
        pass
    fp.close()
    # To delete the cmapx file and the dot file
    os.remove(cmapx_file)
    os.remove(cmapx_file.replace(".cmapx", ""))


def get_project_folder_name_from_filepath(filepath):
    return filepath.split("/")[-2]

def get_workflow_name_from_filepath(filepath):
    return filepath.split("/")[-1]

def get_workflow_link_from_filepath(filepath):
    workflow_html_path =  f"./graphs/{get_project_folder_name_from_filepath(filepath)}/{get_workflow_name_from_filepath(filepath).replace('.dig','.html')}"
    return f'<a href="{workflow_html_path}">View Workflow</a>'

def get_query_file_content(filepath, querypath):
    folder_name = get_project_folder_name_from_filepath(filepath=filepath)
    query_file_absolute_path = "/content/content/project1/queries/example.sql"
    # f"{os.getcwd()}/{folder_name}/{querypath}"
    query_tooltip_text = ""
    with open(query_file_absolute_path, "r") as myfile:
        query_tooltip_text = myfile.readlines()
    # print(f"tooltip: {''.join(query_tooltip_text)} and type is {type(query_tooltip_text)}")
    return "".join(query_tooltip_text)

def create_html_for_scheduled_workflows(table_format):
    with open("scheduled_workflows.html", "a") as scheduled_workflows:
        scheduled_workflows.write(table_format.get_html_string())

def main():
    start_time = time.time()
    count = 0
    for path in Path(os.getcwd()).rglob('*.dig'):
        #if "config" not in str(path) and "proj" not in str(path):
        if "proj" in str(path):
            # and "proj" not in str(path):
            input_file_path = path
            output_dot_file = f"{os.getcwd()}/graphs/{path.parent.name}/{path.name.replace('.dig', '')}"
            logger.info(f'BEGIN generating graph for {input_file_path}')
            generate_graph(input_filepath=str(input_file_path), output_dot_file=str(output_dot_file))
            count = count + 1
            logger.info(f'COMPLETE generating graph for {input_file_path}')
    print(f'Graphs generated: {count} and TIME TAKEN is: {(time.time() - start_time)} seconds')
    pt.attributes = {"name": "scheduled_workflows", "class": "scheduled_workflow_table", "border": "1"}
    create_html_for_scheduled_workflows(pt)


if __name__ == "__main__":
    main()