import os
import webbrowser
from collections import defaultdict, namedtuple

from jinja2 import Environment, FileSystemLoader
from datetime import datetime
from base64 import b64encode

from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter

from .color_reporter import ColorReporter

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
TEMPLATE_FILE = 'template.html'
OUTPUT_FILE = 'output.html'

class HTMLReporter(ColorReporter):
    _COLOURING = {'black': '<span class="black">',
                  'black-line': '<span class="black line-num">',
                  'bold': '<span>',
                  'code-heading': '<span>',
                  'style-heading': '<span>',
                  'code-name': '<span>',
                  'style-name': '<span>',
                  'highlight': '<span class="highlight-pyta">',
                  'grey': '<span class="grey">',
                  'grey-line': '<span class="grey line-num">',
                  'gbold': '<span class="gbold">',
                  'gbold-line': '<span class="gbold line-num">',
                  'reset': '</span>'}
    code_err_title = 'Code Errors or Forbidden Usage (fix: high priority)'
    style_err_title = 'Style or Convention Errors (fix: before submission)'

    def __init__(self, source_lines=None, module_name=''):
        super().__init__(source_lines, module_name)
        self.messages_by_file = []

    def _messages_shown(self, sorted_messages):
        """Trim the amount of messages according to the default number.
        Add information about the number of occurrences vs number shown."""

        max_messages = self.linter.config.pyta_number_of_messages

        MessageSet = namedtuple('MessageSet', 'shown occurrences messages')
        ret_sorted = defaultdict()
        for message_key in sorted_messages:
            message_i_instances = []
            for message_tuple_i in sorted_messages[message_key]:
                # Limit the number of messages shown
                if len(message_i_instances) < max_messages:
                    message_i_instances.append(message_tuple_i)
            ret_sorted[message_key] = MessageSet(shown=len(message_i_instances),
                                                 occurrences=len(sorted_messages[message_key]),
                                                 messages=message_i_instances)
        return dict(ret_sorted)



        # for msg in self._error_messages:
        #     if len(self._sorted_error_messages[msg.msg_id]) < max_messages:
        #         self._sorted_error_messages[msg.msg_id].append(msg)
        #
        # for msg in self._style_messages:
        #     if len(self._sorted_style_messages[msg.msg_id]) < max_messages:
        #         self._sorted_style_messages[msg.msg_id].append(msg)



        # MessageSet(shown=max_messages,
        #            occurances=len(sorted_messages),
        #            sorted_messages=ret_sorted)


    # Override this method
    def print_messages(self, level='all'):
        # Sort the messages.
        self.sort_messages()
        # Call these two just to fill snippet attribute of Messages
        # (and also to fix weird bad-whitespace thing):
        self._colour_messages_by_type(style=False)
        self._colour_messages_by_type(style=True)

        MessageSet = namedtuple('MessageSet', 'filename code style')
        append_set = MessageSet(filename=self.filename_to_display(self.current_file_linted),
                               code=self._messages_shown(self._sorted_error_messages),
                               style=self._messages_shown(self._sorted_style_messages))
        self.messages_by_file.append(append_set)

    def output_blob(self):
        """Output to the template after all messages."""

        template = Environment(loader=FileSystemLoader(TEMPLATES_DIR)).get_template(TEMPLATE_FILE)

        # Embed resources so the output html can go anywhere, independent of assets.
        with open(os.path.join(TEMPLATES_DIR, 'pyta_logo_markdown.png'), 'rb+') as image_file:
            # Encode img binary to base64 (+33% size), decode to remove the "b'"
            pyta_logo_base64_encoded = b64encode(image_file.read()).decode()

        # Set the max number of messages
        # max_messages = self.linter.config.pyta_number_of_messages
        # trim_dict = {key: val for i, (key, val) in enumerate(self.messages_by_file.items()) if i < max_messages}

        # Date/time (24 hour time) format:
        # Generated: ShortDay. ShortMonth. PaddedDay LongYear, Hour:Min:Sec
        dt = str(datetime.now().strftime('%a. %b. %d %Y, %I:%M:%S %p'))
        output_path = os.path.join(os.getcwd(), OUTPUT_FILE)
        with open(output_path, 'w') as f:
            f.write(template.render(date_time=dt,
                                    pyta_logo=pyta_logo_base64_encoded,
                                    reporter=self))
        print('Opening your report in a browser...')
        output_url = 'file:///{}'.format(output_path)
        webbrowser.open(output_url)

    @classmethod
    def _vendor_wrap(self, colour_class, text):
        """Override in reporters that wrap snippet lines in vendor styles, e.g. pygments."""
        if '-line' not in colour_class:
            text = highlight(text, PythonLexer(),
                            HtmlFormatter(nowrap=True, lineseparator='', classprefix='pygments-'))
        return text

    _display = None
