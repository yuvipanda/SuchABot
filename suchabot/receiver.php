<?php
$payload = json_decode( $_POST[ 'payload' ], true );
$repo = $payload[ 'repository' ][ 'name' ];
$number = $payload[ 'number' ];

exec( 'PATH=/bin:/usr/bin:/usr/local/bin /usr/local/bin/jsub -N suchabot -o /data/project/suchaserver/suchabot.out -e /data/project/suchaserver/suchabot.err -mem 512M /data/project/suchaserver/code/SuchABot/suchabot/sync.bash ' . escapeshellarg( $repo ) . ' ' . escapeshellarg( $number ) );
error_log( 'Sync for PR ' . $number . ' of Repo ' . $repo );
