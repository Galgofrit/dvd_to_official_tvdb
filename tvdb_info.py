#!/usr/bin/env python

import sys
import os
import requests
import re
import xmllib
import pprint

OUTPUT_SCRIPT_PATH = 'perform_changes.sh'

SEASON = 'Season'
MOVE_COMMAND = 'cp'
MKDIR_COMMAND = 'mkdir'

FETCH_EPISODES_FROM_SEASON_PAGE_RE = '(S\d\dE\d\d)</span>\n\s*<a href=.*">\n\s*(.*)'
FETCH_SEASON_NUMBER_FROM_ID = 'S(\d.*)E.*'


PATH_TO_EPISODE_NAME = '.*\/?\d (.*)\.(.*)$'
def path_to_episode_name_and_extension(path):
    # returns path, extension
    re_lookup = re.findall(PATH_TO_EPISODE_NAME, path)
    if re_lookup:
        return re_lookup[0]

    return (None, None)


def decode_html_string(string):
    string = string.replace(r'&rsquo;', '\'')
    string = string.replace('&#039;', '\'')
    return string

class DvdOfficialConverterException(Exception):
    pass

class DvdOfficialConverter(object):
    def __init__(self, url, input_path, output_path):
        self._input_path = input_path
        self._output_path = output_path
        self._missing_episodes = []

        self._output_seasons_dirs = []
        self._output_move_commands = []

        sys.stdout.write(' - Looking for series... ')
        sys.stdout.flush()
        try: 
            main_series_response = requests.get(url)
        except:
            raise DvdOfficialConverterException('Couldn\'t get show')
        if main_series_response.status_code != 200:
            raise DvdOfficialConverterException('Couldn\'t get show')
        sys.stdout.write('OK!\n')
        sys.stdout.flush()


        sys.stdout.write(' - Looking for official episode list... ')
        sys.stdout.flush()
        official_season_list_url = '/'.join([url, 'allseasons', 'official'])
        try: 
            official_season_response = requests.get(official_season_list_url)
        except:
            raise DvdOfficialConverterException('Couldn\'t get \'official\' season list')
        if official_season_response.status_code != 200:
            raise DvdOfficialConverterException('Couldn\'t get \'official\' season list')

        official_episode_list = re.findall(FETCH_EPISODES_FROM_SEASON_PAGE_RE, official_season_response.text)
        official_episode_dict = {self.strip_episode_name(decode_html_string(ep_name)): ep_id for (ep_id, ep_name) in official_episode_list}

        sys.stdout.write('OK!\n')
        sys.stdout.flush()


        sys.stdout.write(' - Looking for DVD episode list... ')
        sys.stdout.flush()
        dvd_season_list_url = '/'.join([url, 'allseasons', 'dvd'])
        try: 
            dvd_season_response = requests.get(dvd_season_list_url)
        except:
            raise DvdOfficialConverterException('Couldn\'t get \'dvd\' season list')
        if dvd_season_response.status_code != 200:
            raise DvdOfficialConverterException('Couldn\'t get \'dvd\' season list')

        dvd_episode_list = re.findall(FETCH_EPISODES_FROM_SEASON_PAGE_RE, dvd_season_response.text)
        dvd_episode_dict = {self.strip_episode_name(decode_html_string(ep_name)): ep_id for (ep_id, ep_name) in dvd_episode_list}

        sys.stdout.write('OK!\n')
        sys.stdout.flush()
        
        self._dvd_episode_dict = dvd_episode_dict
        self._official_episode_dict = official_episode_dict

        print 'Loaded {dvd_count} DVD episodes and {official_count} official episoides.'.format(
            dvd_count=len(self._dvd_episode_dict), 
            official_count=len(self._official_episode_dict)
        )
        if (len(self._dvd_episode_dict) != len(self._official_episode_dict)):
            print 'Warning: DVD and official lists have different counts; some episodes might be missing after convertion.'


    def strip_episode_name(self, episode_name):
        episode_name = episode_name.lower()
        episode_name = episode_name.replace(' ', '')
        episode_name = episode_name.replace('.', '')
        episode_name = episode_name.replace(',', '')
        episode_name = episode_name.replace('!', '')
        episode_name = episode_name.replace('?', '')
        episode_name = episode_name.replace('\'', '')
        episode_name = episode_name.replace('\"', '')
        episode_name = episode_name.replace('-', '')
        episode_name = episode_name.replace('the', '')
        return episode_name

    def get_season_number(self, episode_id):
        matches = re.findall(FETCH_SEASON_NUMBER_FROM_ID, episode_id)
        if matches:
            return int(matches[0])

        raise DvdOfficialConverterException('Can\'t fetch season from episode ID {ep_id}'.fomrat(ep_id=episode_id))

    def dvd_to_official(self, path):
        episode_name, extension = path_to_episode_name_and_extension(path)

        if not episode_name or not extension:
            print 'Warning: can\'t process path', path
            self._missing_episodes.append(path)
            return;

        if not self._official_episode_dict.has_key(self.strip_episode_name(episode_name)):
            print 'Warning: can\'t find episode in official list: {path}'.format(path=path)
            self._missing_episodes.append(path)
            return;

        episode_official = self._official_episode_dict[self.strip_episode_name(episode_name)]
        season = self.get_season_number(episode_official)

        if season not in self._output_seasons_dirs:
            self._output_seasons_dirs.append(season)

        return os.path.join(
            self._output_path,
            '{season_desc} {season}'.format(season_desc=SEASON, season=season),
            '{episode_id} {episode_name}.{extension}'.format(
                episode_id=episode_official, 
                episode_name=episode_name, 
                extension=extension
            )
        )

    def generate_move_command(self, from_path, to_path):
        self._output_move_commands.append('%s "%s" "%s"' % (MOVE_COMMAND, from_path, to_path))

    def convert_dir_dvd_to_official(self):
        walker = os.walk(self._input_path)
        for cwd, dirlist, filelist in walker:
            for current_file in filelist:
                current_file_fullpath = os.path.join(cwd, current_file)
                output = self.dvd_to_official(current_file_fullpath)
                if output:
                    self.generate_move_command(current_file_fullpath, output)

        if self._missing_episodes:
            print '\n\n================================'
            print 'Missing episodes ({missing_count}):'.format(missing_count = len(self._missing_episodes))
            pprint.pprint(self._missing_episodes)


    def generate_script(self):
        script = '#!/usr/bin/env bash\n'
        for season in self._output_seasons_dirs:
            season_name = 'Season {season}'.format(season=season)
            script += '{tool} "{path}"'.format(tool=MKDIR_COMMAND, path=os.path.join(self._output_path, season_name))
            script += '\n'

        for move_command in self._output_move_commands:
            script += move_command
            script += '\n'

        return script


def main(args):
    if len(args) != 4:
        print 'usage: {toolname} tvdb_url input_path output_path'.format(toolname=args[0])
        return -1

    dvd_official_converter = DvdOfficialConverter(args[1], args[2], args[3])
    dvd_official_converter.convert_dir_dvd_to_official()

    print '\n'
    with open(OUTPUT_SCRIPT_PATH, 'wb') as output_script:
        output_script.write(dvd_official_converter.generate_script())
        print 'Written {output_scrip_path}.'.format(output_script_path=OUTPUT_SCRIPT_PATH)


if __name__=='__main__':
    sys.exit(main(sys.argv))
