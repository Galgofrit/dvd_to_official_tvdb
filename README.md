
Usage - you might need to rewrite the path_to_episode_name_and_extension function to suit the naming format in your own directory tree
(mine was "203 - Episode Name", where the first 2 was the season number, and the 03 was the episode name).

Other than that - this uses Python 2. It should be easy to migrate to Python 3 (":%s/print \\\(.\*\\\)/print(\1)/g"?)
Just read the usage, and this should generate a "perform_changes.sh" bash script that you should definitely go through before doing "chmod +x" and running blindly.

*Mostly for personal use, feel free to use this however you like.*
