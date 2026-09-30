from pathlib import Path
from thesys_cli.main import main
from thesys_engine.methodology import load_methodology
from thesys_engine.gates import status
import pytest

ROOT=Path(__file__).parents[1]

def cli(*args):
    return main(list(args)+['--path',str(TEST)])

def test_end_to_end_from_human_intent_to_retirement(tmp_path,monkeypatch):
    global TEST; TEST=tmp_path
    assert cli('init')==0
    assert cli('intent','create','Build a personal finance platform for income, expenses, budgets, analytics and secure authentication.')==0
    assert cli('discovery','propose','--agent','mock')==0
    assert cli('discovery','accept')==0
    assert status(tmp_path,load_methodology(ROOT))['intent']['status']=='approved'
    assert cli('generate','governance','--agent','mock')==0
    assert cli('proposal','accept','governance')==0
    assert cli('generate','context','--agent','mock')==0
    assert cli('proposal','accept','context')==0
    for stage in ['requirements','clarification','specification','acceptance','architecture','system-architecture','quality','security','risk','plan','tasks']:
        assert cli('generate',stage,'--agent','mock')==0
        assert cli('proposal','accept',stage)==0
    assert cli('implementation','propose','--agent','mock')==0
    assert cli('implementation','accept')==0
    assert (tmp_path/'src/main.py').is_file()
    import subprocess
    class Result:
        returncode=0
        stdout='project verification passed'
        stderr=''
    monkeypatch.setattr(subprocess, 'run', lambda *args, **kwargs: Result())
    assert cli('verify','--agent','mock')==0
    assert cli('proposal','accept','verification')==0
    for stage in ['convergence','release','operation','evolution','retirement']:
        assert cli('generate',stage,'--agent','mock')==0
        assert cli('proposal','accept',stage)==0
    st=status(tmp_path,load_methodology(ROOT))
    assert all(x['status'] in {'approved','completed'} for x in st.values())

def test_no_stage_can_be_approved_without_ai_proposal(tmp_path):
    global TEST; TEST=tmp_path
    cli('init')
    assert cli('intent','create','Build a system.')==0
    with pytest.raises(Exception):
        cli('discovery','accept')
