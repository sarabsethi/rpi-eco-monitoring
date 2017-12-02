uncomp_fname=$1
final_comp_fname=$2
temp_comp_fname=$uncomp_fname.mp3

avconv -loglevel panic -i $uncomp_fname -codec:a libmp3lame -filter:a "volume=5" -qscale:a 0 -ac 1 $temp_comp_fname >/dev/null 2>&1

mv $temp_comp_fname $final_comp_fname
rm $uncomp_fname
