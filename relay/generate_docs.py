import inspect
import sys
import workflow
import pydoc

p = pydoc.HTMLDoc()

with open("workflow.html", "w") as write_html:
    write_html.write(p.docmodule(sys.modules["workflow"]))

for name, obj in inspect.getmembers(workflow):
    if inspect.isclass(obj):
        with open(name + ".html", "w") as write_html:
            write_html.write(p.docclass(obj))
