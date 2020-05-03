" misc-bindings.vim
" Every miscellaneous key binding will go here.

" << That stupid goddamned help key that you will invaribly hit constantly
" while aiming for escape >> -- Steve Losh
inoremap <F1> <Esc>
vnoremap <F1> <Esc>
nnoremap <F1> <Esc>

" << it's one less key to hit every time I want to save a file >>
"   -- Steve Losh (again)
nnoremap ; :
vnoremap ; :

" From Kalenz's Vim config. Life changing.
nnoremap <Space> <C-w>

" halfr personnal shortcurts
nnoremap <Space>\| <C-w>v<Return>
nnoremap <Space>- <C-w>s<Return>
nnoremap <Space><Space> <C-w>w

" save
nnoremap <Space><Return> :w<Return>
" save and quit
nnoremap <Space><Backspace> :x<Return>

nnoremap <Space>! :tab sball<Return>

nnoremap <F5> :make<Return>

" I DONT WANT TO USE AN ENCRYPTION KEY
" http://stackoverflow.com/questions/3878692/aliasing-a-command-in-vim
cnoreabbrev <expr> X ((getcmdtype() is# ':' && getcmdline() is# 'X')?('x'):('X'))
