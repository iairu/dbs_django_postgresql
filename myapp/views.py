from django.shortcuts import render
from django.http import HttpResponse

from .models import sql_query_one # priama SQL podpora
import json

# Create your views here.
def index(request):
    return HttpResponse("""
        <h1>Hello FIIT!</h1>
        <h2>Content</h2>
        <nav>
            <a href=\"/v1/health\">/v1/health</a><br>
        </nav>
        <h2>Relevant stuff</h2>
        <nav>
            <a href=\"https://github.com/FIIT-DBS/zadanie-stv8-binder-iairu\">github repo</a><br>
            <a href=\"https://iairu.com\">iairu.com</a>
        </nav>
    """)

def v1_health(request):
    # content_type a pod.: https://docs.djangoproject.com/en/4.0/ref/request-response/#id4
    # django ma namiesto HttpResponse aj JsonResponse, ale mam pocit ze pointa bola precvicit si manualne MIME type nastavenie
    return HttpResponse(
        json.dumps({"pgsql":{ # spojenie dvoch dict do jedneho cez unpack operator **
            **sql_query_one("SELECT VERSION()"), 
            **sql_query_one("SELECT pg_database_size('dota2')/1024/1024 as dota2_db_size")
            }}), content_type="application/json; charset=utf-8")