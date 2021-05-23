new_cache = {'test': {1: 'hi', 2: 'wat'}}
new_cache['test']['new_post_id2'] = 'post'


print (new_cache['test2'].get('new_post_id', 'wat'))