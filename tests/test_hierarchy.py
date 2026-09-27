from pathlib import Path
from thesys_cli.main import main
from thesys_engine.methodology import load_methodology
from thesys_engine.gates import status
ROOT=Path(__file__).parents[1]

def test_project_and_unit_scopes_are_distinct(tmp_path):
    main(['init','--path',str(tmp_path)])
    main(['intent','create','Build a platform with accounts and analytics.','--path',str(tmp_path)])
    main(['discovery','propose','--agent','mock','--path',str(tmp_path)])
    main(['discovery','accept','--path',str(tmp_path)])
    main(['generate','governance','--agent','mock','--path',str(tmp_path)])
    main(['proposal','accept','governance','--path',str(tmp_path)])
    main(['unit','create','accounts','Accounts','--type','module','--scope','Account management','--path',str(tmp_path)])
    m=load_methodology(ROOT)
    assert status(tmp_path,m,'accounts')['intent']['status']=='approved'
    assert status(tmp_path,m,'accounts')['governance']['status']=='approved'
    assert status(tmp_path,m,'accounts')['context']['status']=='missing'
    assert main(['generate','context','--unit','accounts','--agent','mock','--path',str(tmp_path)])==0
    assert main(['proposal','accept','context','--unit','accounts','--path',str(tmp_path)])==0
    assert status(tmp_path,m,'accounts')['context']['status']=='approved'
