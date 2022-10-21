import inspect
import os
import relay.workflow

os.chdir('../relay')
os.system('ls')
os.system('pydoc3 -w workflow')
for name, obj in inspect.getmembers(relay.workflow):
    if inspect.isclass(obj):
        os.system('pydoc3 -w workflow.%s' % name)
