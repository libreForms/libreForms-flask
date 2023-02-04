""" 
celeryd/__init__.py: the init script for the libreForms celery app

This application has toyed with implementing celery at a number of
different points, to manage long-running background tasks & set up
scheduled tasks without needing to manage CRON. Because the web
application employs the Flask factory pattern, there are some 
complexities implementing celery - we borrow heavily from Miguel
Grinberg's approach to Celery using the factory pattern, described here:
https://blog.miguelgrinberg.com/post/celery-and-the-flask-application-factory-pattern

The celery app is created in app/__init__.py, but stored as a global 
variable. Then, we push the app context from within create_app().
Now, we'll import that here and treat this as the module - separate
from the main application context - from which celery will be 
invoked by systemd. For awhile, we attempted to run this script
from within app/__init__.py, but this approach proved to be 
insufficiently robust because, it seems, the celery object was
being accessed from systemd without passing the app context,
as create app was not being run.

One area that we still need to confirm: whether to create the celery
tasks within the application context, or outside it. Our initial hunch 
is that we should write these tasks within the app context, which we 
access here, but we'll continue to troubleshoot as this approach
inevitably evolves.

Even so, because of potential module name confusion (too many objects / 
modules can be access using the phrase `app.celery`), we opted to place
this script in the application working directory.

"""

__name__ = "celeryd"
__author__ = "Sig Janoska-Bedi"
__credits__ = ["Sig Janoska-Bedi"]
__version__ = "1.5.0"
__license__ = "AGPL-3.0"
__maintainer__ = "Sig Janoska-Bedi"
__email__ = "signe@atreeus.com"

# import any relevant tasks defined in celeryd outside the app context
from celeryd.tasks import send_mail_async, write_document_to_collection_async

# import flask app specific dependencies
from app import create_app, celery, log, mongodb
from app.filters import send_eligible_reports

# import the libreforms form config
from libreforms import forms

# import data management tools
import pandas as pd

# import date tools
from datetime import datetime
from dateutil import parser

app = create_app(celery_app=True)
app.app_context().push()

@celery.task()
def send_eligible_reports_async(*arg, **kwargs):
    return send_eligible_reports(*arg, **kwargs)


# this should run periodically to refresh the elasticsearch index 
@celery.task()
def elasticsearch_refresh_index():
    pass


@celery.task()
def celery_beat_logger():
    log.info('LIBREFORMS - celery just had another hearbeat.')
    return 'LIBREFORMS - celery just had another hearbeat.'


def convert_timestamp(row, now):
    # print(now)
    t = datetime.timestamp(parser.parse(row[mongodb.metadata_field_names['timestamp']]))
    # print(t)
    return now - t
    


@celery.task()
def index_new_documents(elasticsearch_index="submissions"):

    # log.info(f'LIBREFORMS - started elasticsearch index process.')

    # here we exclude forms explicitly exlucded from search indexing.
    form_list = [x for x in forms if x not in app.config["EXCLUDE_FORMS_FROM_SEARCH"]]
    
    # for each of these form names
    for f in form_list:
        
        # log.info(f'LIBREFORMS - stated elasticsearch index for form {f}.')   

        # get all the documents in the collection
        df = mongodb.new_read_documents_from_collection(f)

        # mongodb.new_read_documents_from_collection() returns False if no collection
        # exists with that name, so we can save ourselves an otherwise wasted iteration
        # here if any given form is not of type `DataFrame`
        if not isinstance(df, pd.DataFrame):
            print(f,' - empty collection - type: ', type(df))
            continue

        # print(df)
        print(f, ' - found data - type: ', type(df))

        # stringify the BSON data
        df['_id'] = df.apply(lambda row: str(row['_id']), axis=1)

        # drop the unnecessary columns
        df.drop(columns=[x for x in mongodb.metadata_fields() if x in df.columns], inplace=True)

        # we iterate through rows
        for index, row in df.iterrows():

            id = row['_id']

            print(f'{f} - {id}')

            # we write a little string to approximate the page content of the corresponding page; nb. we 
            # exclude certain fields that are not 'content' fields...
            fullString = ', '.join([f'{x} - {str(row[x])}' for x in df.columns if x not in mongodb.metadata_fields(exclude_id=True)])

            # this is the new form data we want to pass
            v2_elasticsearch_content = dict(row)

            # remove the _id field from the content
            del v2_elasticsearch_content['_id']

            # we construct the body payload for elasticsearch
            elasticsearch_data = {
                'formName': f,
                'title': id,
                'url': f"/submissions/{f}/{id}", 
                # 'url': url_for('submissions.render_document', form_name=f, document_id=str(row._id)), 
                # let's consider adding a different `_all` field, which we can call `fullString`. Here are some references
                # that this 
                #   https://www.elastic.co/guide/en/elasticsearch/reference/6.0/mapping-all-field.html#custom-all-fields
                #   https://stackoverflow.com/a/34147611/13301284
                'fullString': fullString,
                **v2_elasticsearch_content, # pass the row data from above as kwargs
            }

            # let's stringify each element for now, just for simplicity; otherwise, we are receiving the following error:
            # elasticsearch.exceptions.RequestError: RequestError(400, 'mapper_parsing_exception', 'failed to parse')
            # if we want to have better typing, we should probably add a DocType object from elasticsearch-dsl
            for key in elasticsearch_data:
                elasticsearch_data[key] = str(elasticsearch_data[key])
            
            # write the item to the elasticsearch index 
            app.elasticsearch.index(id=id, body=elasticsearch_data, index=elasticsearch_index)

            # log.info(f'LIBREFORMS - updated search index for document no. {document_id}.')

    # log.info(f'LIBREFORMS - finished elasticsearch index process.')



@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):

    if app.config["USE_ELASTICSEARCH_AS_WRAPPER"]:

        # periodically calls send_reports 
        sender.add_periodic_task(app.config["REPORT_SEND_RATE"], send_eligible_reports_async.s(), name='send reports periodically')

    # periodically conduct a heartbeat check
    sender.add_periodic_task(3600.0, celery_beat_logger.s(), name='log that celery beat is working')

    # periodically update the elasticsearch index, giving a slightly longer `time_since`
    # to avoid delay problems. We might be able to design this better ... This value ultimately
    # derives from the `elasticsearch_index_refresh_rate` app config.
    sender.add_periodic_task(app.config["ELASTICSEARCH_INDEX_REFRESH_RATE"], index_new_documents.s(), name='update elasticsearch index')