from django.db import models, connections


def _dict_fetch_one(cursor): 
    # z Django docs https://docs.djangoproject.com/en/4.0/topics/db/sql/#executing-custom-sql-directly
    columns = [col[0] for col in cursor.description]
    # return [dict(zip(columns, row)) for row in cursor.fetchall()] # povodne: vsetky zaznamy
    # return dict(zip(columns, (cursor.fetchone(), cursor.fetchone()))) # dva zaznamy
    return dict(zip(columns, (cursor.fetchone()))) # jeden zaznam

# Create your models here.
def sql_query_one(cursor_query: str): 
    # z Django docs https://docs.djangoproject.com/en/4.0/topics/db/sql/#executing-custom-sql-directly
    # treba opatrne s SQL, pretoze sa nad nim robia nejake upravy (napr. neukoncuje sa s ;), vid dokumentaciu
    with connections['readonly'].cursor() as cursor:
        cursor.execute(cursor_query)
        out = _dict_fetch_one(cursor)
    return out
