import inspect
import os
from relay import workflow

os.system('pydoc3 -w workflow')
for name, obj in inspect.getmembers(workflow):
    if inspect.isclass(obj):
        os.system('pydoc3 -w workflow.%s' % name)
