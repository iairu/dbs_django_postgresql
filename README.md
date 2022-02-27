Ondrej Špánik

```
Python 3.10.2
Django 4.0
```

## Sprevádzkovanie

1. jednorázovo: `python -m venv venv` vytvorí virtuálny environment
2. `venv/Scripts/activate.bat` pre **aktiváciu virtuálneho environmentu** 

> prípadne na linuxoch to môže byť `./venv/bin/activate`, názov je hlavný

3. **environment variables aktivácia** cez `env_dev.bat` (lokálna DB u mňa alebo `env_prod.bat` pre lokálne použitie FIIT databázy zo zadania) 

> nie je súčasť repozitára kvôli bezpečnosti, obsah je nasledovný:

```powershell
@echo off
set DBHOST=zo zadania pre env_prod alebo lokalna pre env_dev
set DBNAME=dota2
set DBUSER=ais login
set DBPASS=ais heslo
set DEBUG=0 ak to je env_prod a 1 ak env_dev
set SECRET_KEY=nieco nahodne som prebehol cez SHA-1
```

4. nepovinné: kontrola funkčnosti venv pomocou `which python` alebo `where python`

> ak sa nepoužíva python v lokálnej venv zložke, tak treba venv odstrániť, reinštalovať python (ideálne na spomenutú verziu) a ísť od 1.
>
> u mňa sa tento problém vyskytol pretože môj msys2 mingw sa rozhodol byť preferovaný v PATH a teda som používal niečo ako "unixový build pythonu na windowse", nemal som ani activate.bat a venv odmietal akokoľvek fungovať

5. jednorázovo: `pip install -r requirements.txt` pre inštaláciu packages

6. hotovo, ak je správne nakonfigurovaný prístup k DB tak by mal fungovať Django webserver pomocou `python manage.py runserver`

> v budúcnosti už treba aplikovať len 2. a 3. krok po otvorení terminálu a pred prácou s manage.py