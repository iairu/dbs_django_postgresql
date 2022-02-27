from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.
def index(request):
    return HttpResponse("""
        <h1>Hello FIIT!</h1>
        <h2>Relevant stuff</h2>
        <nav>
            <a href=\"https://github.com/FIIT-DBS/zadanie-stv8-binder-iairu\">github repo</a><br>
            <a href=\"https://iairu.com\">iairu.com</a>
        </nav>
    """)
