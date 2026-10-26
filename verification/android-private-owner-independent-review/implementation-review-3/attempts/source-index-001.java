import com.sun.source.tree.ClassTree;
import com.sun.source.tree.CompilationUnitTree;
import com.sun.source.tree.MethodInvocationTree;
import com.sun.source.tree.MethodTree;
import com.sun.source.util.JavacTask;
import com.sun.source.util.SourcePositions;
import com.sun.source.util.TreePathScanner;
import com.sun.source.util.Trees;
import java.util.ArrayList;
import java.util.List;
import javax.tools.DiagnosticCollector;
import javax.tools.JavaFileObject;
import javax.tools.ToolProvider;

/** Official javac AST identity index only. Does not analyze/compile/run product bodies. */
public final class SourceCallIndex {
    private SourceCallIndex() {}
    private static String quote(String value) {
        return "\""+value.replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n").replace("\r","\\r")+"\"";
    }
    public static void main(String[] args)throws Exception {
        var compiler=ToolProvider.getSystemJavaCompiler();
        if(compiler==null)throw new IllegalStateException("official javac API required");
        var diagnostics=new DiagnosticCollector<JavaFileObject>();
        try(var files=compiler.getStandardFileManager(diagnostics,null,null)) {
            var task=(JavacTask)compiler.getTask(null,files,diagnostics,List.of("-proc:none","--release","17"),null,files.getJavaFileObjects(args));
            var parsed=task.parse();SourcePositions positions=Trees.instance(task).getSourcePositions();
            for(CompilationUnitTree unit:parsed) {
                List<String> classes=new ArrayList<>(),methods=new ArrayList<>();
                new TreePathScanner<Void,Void>() {
                    @Override public Void visitClass(ClassTree tree,Void ignored) {
                        String name=tree.getSimpleName().toString();classes.add(name.isEmpty()?"<anonymous>":name);
                        try{return super.visitClass(tree,ignored);}finally{classes.remove(classes.size()-1);}
                    }
                    @Override public Void visitMethod(MethodTree tree,Void ignored) {
                        List<String> parameters=new ArrayList<>();
                        for(var parameter:tree.getParameters()) {
                            String type=parameter.getType().toString().replace(" ","");
                            if(!type.equals("Mutation")&&!type.endsWith(".Mutation"))parameters.add(type);
                        }
                        methods.add(tree.getName()+"("+String.join(",",parameters)+")");
                        try{return super.visitMethod(tree,ignored);}finally{methods.remove(methods.size()-1);}
                    }
                    @Override public Void visitMethodInvocation(MethodInvocationTree tree,Void ignored) {
                        long start=positions.getStartPosition(unit,tree),end=positions.getEndPosition(unit,tree);
                        System.out.println("{\"source\":"+quote(unit.getSourceFile().getName())+",\"classes\":"+quote(String.join("/",classes))+",\"methods\":"+quote(String.join("/",methods))+",\"select\":"+quote(tree.getMethodSelect().toString())+",\"arguments\":"+tree.getArguments().size()+",\"start\":"+start+",\"end\":"+end+",\"line\":"+unit.getLineMap().getLineNumber(start)+",\"column\":"+unit.getLineMap().getColumnNumber(start)+"}");
                        return super.visitMethodInvocation(tree,ignored);
                    }
                }.scan(unit,null);
            }
            if(diagnostics.getDiagnostics().stream().anyMatch(d->d.getKind()==javax.tools.Diagnostic.Kind.ERROR))
                throw new IllegalStateException("parse diagnostics: "+diagnostics.getDiagnostics());
        }
    }
}
