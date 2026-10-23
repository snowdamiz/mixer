package dev.mixer.android;
import java.nio.file.*;
final class EnginePackets {
    public static void main(String[] args) throws Exception {
        Path folder = Path.of(args[0]);
        UiPacket checklist = UiPacket.decode(Files.readAllBytes(folder.resolve("checklist.json")));
        UiPacket document = UiPacket.decode(Files.readAllBytes(folder.resolve("document.json")));
        if (!checklist.revision.equals("1") || !checklist.root.id.equals("screen")
            || !checklist.nodes.get("draft").actions.get("textChange").equals("draft.change")
            || !checklist.nodes.get("add").disabled
            || !document.revision.equals("1") || document.nodes.size() != 3
            || !document.nodes.get("text").text("text", "").equals("é\0漢字🏗️")
            || !document.nodes.get("button").actions.get("activate").equals("save")) {
            throw new AssertionError("actual engine packet mismatch");
        }
        System.out.println("PASS: actual checklist/document engine packets accepted by production decoder");
    }
}
