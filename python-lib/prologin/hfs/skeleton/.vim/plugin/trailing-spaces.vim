" trailing-spaces.vim
" Trailing whitespaces highlighting

highlight ExtraWhitespace ctermbg=darkred
" Show trailing whitepace and spaces before a tab:
autocmd Syntax * syn match ExtraWhitespace /\s\+$\| \+\ze\t/
