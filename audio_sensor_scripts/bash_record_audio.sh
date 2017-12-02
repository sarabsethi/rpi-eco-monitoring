# first arg is duration, second is fname, third is temp fname
dur=$1
final_fname=$2
temp_fname=$3

sudo arecord --device hw:1,0 --rate 44100 --format S16_LE --duration $dur $temp_fname

mv $temp_fname $final_fname
