fn require_same<T>(_:&T,_:&T){}
fn main(){let value=1usize;let closure=||value;let tuple=(&value,);require_same(&closure,&tuple);}
