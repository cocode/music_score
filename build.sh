#!/bin/bash

set -euo pipefail

python3 render_score.py french_slow_waltz.json
python3 render_score.py german_waltz.json
python3 render_score.py jette_waltz.json
python3 render_score.py sauteuse_waltz.json

