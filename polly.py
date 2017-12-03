# encoding: utf-8
import subprocess
import tempfile
import click
import os


command = 'aws polly synthesize-speech --text-type text --output-format "mp3" --voice-id "Joanna" --text "{0}" {1}'


class Polly:
    def __init__(self):
        pass

    @staticmethod
    @click.command()
    @click.option('--input-file', required=True)
    @click.option('--output-file', required=True)
    @click.option('--start-page', type=int, help='Begin parsing this book when the start page number is detected.'
                                                 'By default the start page will be the first page in the book.')
    @click.option('--end-page', type=int,
                  help='Stop parsing the book after the endpage number is detected. By default this will stop '
                       'parsing the book at the last line in the book.')
    @click.option('--remove-page-numbers/--keep-page-numbers', default=True, help='Do not read page numbers aloud.')
    def create_audio_book(input_file, output_file, start_page, end_page, remove_page_numbers):

        with tempfile.TemporaryFile() as formatted_temp_file:
            Polly.format_book_to_temp_file(input_file, formatted_temp_file, start_page, end_page, remove_page_numbers)

            # return to first line of temp file
            formatted_temp_file.seek(0)

            # main loop
            with open(output_file, 'w') as out:
                chunk = Polly.get_polly_chunk(formatted_temp_file)
                while chunk:
                    with tempfile.NamedTemporaryFile() as polly_out:
                        subprocess.call(command.format(chunk, polly_out.name), shell=True)
                        out.write(polly_out.read())
                        chunk = Polly.get_polly_chunk(formatted_temp_file)

    @staticmethod
    def get_polly_chunk(in_file):
        text = ""
        # polly has a 1500 char limit, below is a heuristic to craft text chunks smaller than polly's limit
        for line in in_file:
            text += line
            if len(text) > 1150:
                break
        # the command string cannot have " in the raw text
        text = text.replace('"', '\\"').replace('\n', ' ')
        # amazon expects utf-8 encoding
        return text.decode("utf-8", errors='ignore').encode("utf-8")

    @staticmethod
    def format_book_to_temp_file(file_name, out_file, start_page=None, last_page=None, remove_page_numbers=True):

        with open(file_name, 'r') as in_file:
            if start_page is not None:
                Polly.skip_to_start_line(in_file, start_page)

            Polly.write_lines(in_file, out_file, last_page, remove_page_numbers)

    @staticmethod
    def skip_to_start_line(file, start_page_num):
        # write output to dev null because we want to ignore all output up to start page
        with open(os.devnull, 'w') as dev_null:
            Polly.write_lines(file, start_page_num, dev_null)

    @staticmethod
    def write_lines(file, out_file, stop_page_num=None, remove_page_numbers=True):
        found_stop_page = False

        for line in file:
            formatted_line = line.strip()

            if formatted_line == "" or formatted_line is None:
                continue

            if Polly.is_page_number_line(formatted_line):
                if stop_page_num is not None and stop_page_num in formatted_line:
                    found_stop_page = True
                    break

                if remove_page_numbers:
                    continue

            out_file.write(formatted_line + '\n')

        if not found_stop_page and stop_page_num is not None:
            raise RuntimeError("Could not find supplied page number {}".format(stop_page_num))

    # this function could remove real lines that start with a number, but in the general case this works
    @staticmethod
    def is_page_number_line(line):
        line_list = line.split()
        return line_list[0].isdigit() or line_list[-1].isdigit()


if __name__ == '__main__':
    Polly.create_audio_book()
