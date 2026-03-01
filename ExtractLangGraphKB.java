import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.HashSet;
import java.util.Set;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceManager;
import ghidra.util.task.ConsoleTaskMonitor;

public class ExtractLangGraphKB_V3 extends GhidraScript {


    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length == 0) {
            println("[-] FATAL: No output path provided by Python. Exiting.");
            return;
        }
        String EXPORT_PATH = args[0];
        
        if (currentProgram == null) return;

        FunctionManager fm = currentProgram.getFunctionManager();
        ReferenceManager refMan = currentProgram.getReferenceManager();
        DecompInterface decomp = new DecompInterface();
        decomp.openProgram(currentProgram);
        ConsoleTaskMonitor monitor = new ConsoleTaskMonitor();

        JsonObject rootKb = new JsonObject();

        for (Function func : fm.getFunctions(true)) {
            if (func.isThunk() || func.isExternal()) continue;

            JsonObject funcObj = new JsonObject();
            funcObj.addProperty("address", func.getEntryPoint().toString());
            funcObj.addProperty("signature", func.getSignature().getPrototypeString());

            JsonArray internalCalls = new JsonArray();
            JsonArray apiCalls = new JsonArray();
            JsonArray dataRefs = new JsonArray();
            Set<String> internalSet = new HashSet<>();
            Set<String> apiSet = new HashSet<>();
            Set<String> dataSet = new HashSet<>();

            // 1. Analyze Outbound References (Calls and Data/Strings)
            for (Reference ref : refMan.getReferencesFrom(func.getBody())) {
                if (ref.getReferenceType().isCall()) {
                    Function calledFunc = fm.getFunctionAt(ref.getToAddress());
                    if (calledFunc != null) {
                        if (calledFunc.isExternal() || calledFunc.isThunk()) {
                            if (apiSet.add(calledFunc.getName())) apiCalls.add(calledFunc.getName());
                        } else {
                            if (internalSet.add(calledFunc.getName())) internalCalls.add(calledFunc.getName());
                        }
                    }
                } else if (ref.getReferenceType().isData()) {
                    Data data = currentProgram.getListing().getDataAt(ref.getToAddress());
                    if (data != null && data.hasStringValue()) {
                        String strVal = data.getDefaultValueRepresentation();
                        if (dataSet.add(strVal)) dataRefs.add(strVal);
                    }
                }
            }
            funcObj.add("calls_internal", internalCalls);
            funcObj.add("calls_api", apiCalls);
            funcObj.add("strings_referenced", dataRefs);

            // 2. Analyze Inbound References (XREFs / Callers)
            JsonArray callers = new JsonArray();
            Set<String> callerSet = new HashSet<>();
            for (Reference ref : refMan.getReferencesTo(func.getEntryPoint())) {
                if (ref.getReferenceType().isCall()) {
                    Function callerFunc = fm.getFunctionContaining(ref.getFromAddress());
                    if (callerFunc != null && callerSet.add(callerFunc.getName())) {
                        callers.add(callerFunc.getName());
                    }
                }
            }
            funcObj.add("called_by", callers);

            // 3. Instruction Count & Raw Assembly (Fallback)
            InstructionIterator instIter = currentProgram.getListing().getInstructions(func.getBody(), true);
            int instCount = 0;
            StringBuilder asmBuilder = new StringBuilder();
            while (instIter.hasNext() && instCount < 500) { // Cap at 500 instructions to save JSON size
                Instruction inst = instIter.next();
                asmBuilder.append(inst.getAddressString()).append(" ")
                          .append(inst.getMnemonicString()).append(" ")
                          .append(inst.getDefaultOperandRepresentation()).append("\n");
                instCount++;
            }
            funcObj.addProperty("instruction_count", instCount);
            if (instCount >= 500) asmBuilder.append("... [TRUNCATED] ...\n");
            
            // 4. Decompile
            DecompileResults results = decomp.decompileFunction(func, 30, monitor);
            if (results.decompileCompleted()) {
                funcObj.addProperty("c_code", results.getDecompiledFunction().getC());
                // Only provide assembly if decompilation fails or if the function is very small (thunk-like)
                funcObj.addProperty("assembly", instCount < 20 ? asmBuilder.toString() : "Omitted (Decompilation Successful)");
            } else {
                funcObj.addProperty("c_code", "// DECOMPILATION FAILED");
                funcObj.addProperty("assembly", asmBuilder.toString()); // Crucial fallback for the AI
            }

            rootKb.add(func.getName(), funcObj);
        }

        File outFile = new File(EXPORT_PATH);
        outFile.getParentFile().mkdirs();
        try (FileWriter writer = new FileWriter(outFile)) {
            Gson gson = new GsonBuilder().setPrettyPrinting().create();
            gson.toJson(rootKb, writer);
            println("[+] V3 LangGraph KB built successfully at: " + EXPORT_PATH);
        } catch (IOException e) {
            println("[-] Error writing JSON: " + e.getMessage());
        } finally {
            decomp.dispose();
        }
    }
}