" Dettorer's ToggleBepo
let g:bepo_enable=0
function! ToggleBepo()
    if g:bepo_enable == 0
        let g:bepo_enable=1
        set langmap=$`,\\"1,«2,»3,(4,)5,@6,+7,-8,/9,*0,=-,%=,bq,éw,pe,or,èt,^y,vu,di,lo,jp,z[,w],aa,us,id,ef,\\,g,ch,tj,sk,rl,n:,m',ç\\\\,ê<,àz,yx,xc,.v,kb,'n,qm,g\\,,h.,f/,#~,1!,2@,3#,4$,5%,6^,7&,8*,9(,0),°_,`+,BQ,ÉW,PE,OR,ÈT,!Y,VU,DI,LO,JP,Z{,W},AA,US,ID,EF,\\;G,CH,TJ,SK,RL,N:,M\\",Ç\\|,Ê>,ÀZ,YX,XC,:V,KB,?N,QM,G<,H>,F?
        set langnoremap
    else
        let g:bepo_enable=0
        set langmap=
    endif
endfunction
noremap <F12> :call ToggleBepo()<CR>
