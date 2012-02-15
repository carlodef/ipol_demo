#!/bin/bash

ssh fuchsia "cd ipol/; ./stop.sh";

rsync -avz --delete -e ssh ./ fuchsia:~/ipol/demo/ --exclude=demo.conf* --exclude=app/*/tmp/ --exclude=app/*/archive/ --exclude=app/*/bin/ --exclude=app/*/src/ --exclude=app/*/dl/ --exclude=.git;

ssh fuchsia "cd ipol/demo/; rm -r app/*/tmp app/*/bin/ app/*/dl";

ssh fuchsia "cd ipol/; ./start.sh"
