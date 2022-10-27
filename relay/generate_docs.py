import inspect
import sys
import workflow
import pydoc

p = pydoc.HTMLDoc()
func = open("workflow.html", "w")
func.write(p.docmodule(sys.modules["workflow"]))
func.close()
for name, obj in inspect.getmembers(workflow):
    if inspect.isclass(obj):
        func = open(name + ".html", "w")
        func.write(p.docclass(obj))
        func.close()
