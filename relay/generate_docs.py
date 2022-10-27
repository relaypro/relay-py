import inspect
import sys
import workflow
import pydoc

p = pydoc.HTMLDoc()

write_html = open("workflow.html", "w")
write_html.write(p.docmodule(sys.modules["workflow"]))
write_html.close()

for name, obj in inspect.getmembers(workflow):
    if inspect.isclass(obj):
        write_html = open(name + ".html", "w")
        write_html.write(p.docclass(obj))
        write_html.close()
