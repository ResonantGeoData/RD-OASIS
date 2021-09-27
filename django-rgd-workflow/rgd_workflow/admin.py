from django.db.models import FileField
from django.template.defaultfilters import linebreaksbr
from django.utils.html import escape
from django.utils.safestring import mark_safe


def _text_preview(target_file: FileField, mimetype=None, show_end=True):
    """
    Return the text of a file if it is short or a portion of it if it is long.

    params:
        target_file: A FileField to read text from. (log or data file)
        mimetype: A string default to be 'None' for log (data file have a mimetype)
        show_end: A bool default to be True determines first/last portion for preview
    """
    # show log file preview while data file needs to be checked
    mimetype_check = mimetype is None or (mimetype is not None and mimetype.startswith('text/'))
    # if mimetype_check fails, no need to read files
    if not mimetype_check:
        return None
    # max file size for display, currently 10kb
    maxlen = 10000
    if target_file:
        with target_file.open('rb') as datafile:
            if len(datafile) > 0:
                if show_end:
                    # read and only display from the end for log filess
                    display_message = 'last'
                    # seek reference
                    datafile.seek(max(0, len(target_file) - maxlen))
                else:
                    # no need for seek reference if start with the beginning
                    display_message = 'first'
                message = datafile.read(maxlen).decode(errors='replace')
                if len(target_file) < maxlen:
                    return mark_safe('<PRE>' + escape(message) + '</PRE>')
                else:
                    prefix_message = f"""The output is too large to display in the browser.
                Only the {display_message} {maxlen} characters are displayed.
                """
                    prefix_message = linebreaksbr(prefix_message)
                    return mark_safe(prefix_message + '<PRE>' + escape(message) + '</PRE>')
            else:
                return 'File is empty'
    else:
        return 'No file provided'
