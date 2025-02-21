from fasthtml.common import *
from shad4fast import *

def get_upload_card():
    return Card(
        Div(
            Form(
                Div(
                    Div(
                        P("Upload your CV PDF file and click 'Process' to extract details.",
                          cls="text-sm text-gray-400 text-center"),
                        cls="space-y-1.5 p-4 md:p-6 items-center justify-center"
                    ),
                    Div(
                        Input(
                            type="file",
                            name="pdf_document",
                            accept="application/pdf",
                            cls="hidden",
                            id="file-upload-pdf",
                            hx_post="/upload-pdf",
                            hx_encoding="multipart/form-data",
                            hx_target="#information-display",
                            hx_trigger="change"
                        ),
                        Label(
                            Lucide("file-text", cls="w-8 h-8 md:w-10 md:h-10 mb-2 text-blue-400 float"),
                            "Click to upload CV (pdf)",
                            htmlFor="file-upload-pdf",
                            cls="flex flex-col items-center justify-center w-full h-32 md:h-40 border-2 border-dashed border-blue-400 rounded-lg cursor-pointer hover:bg-blue-400/5 backdrop-blur-sm transition-all duration-200 glass hover-lift text-gray-300 text-sm md:text-base"
                        ),
                    ),
                    id="upload-container-pdf",
                ),
                Div(
                    Button(
                        Div(
                            "Process",
                            cls="processing-btn process-btn-state items-center justify-center text-sm md:text-base"
                        ),
                        Div(
                            Lucide("loader", cls="w-4 h-4 mr-2 spinner"),
                            "Processing... please wait",
                            cls="loading-btn process-btn-state items-center justify-center text-xs md:text-sm"
                        ),
                        variant="outline",
                        type="button",
                        cls="pulse w-full bg-blue-400/10 hover:bg-blue-400/20 border-white/40 hover:border-blue-400 hover:text-white text-white",
                        hx_post="/process-pdf",
                        hx_target="#information-display",
                        hx_indicator="#process-btn-pdf",
                        id="process-btn-pdf"
                    ),
                    Button(
                        "Clear Document",
                        variant="outline",
                        cls="w-full bg-red-400/10 hover:bg-red-400/20 border-red-400/30 hover:border-red-400 hover:text-white text-white text-sm md:text-base",
                        hx_post="/clear-pdf",
                        hx_target="#information-display"
                    ),
                    cls="gap-3 md:gap-6 pt-4 md:pt-6 grid w-full grid-cols-1 md:grid-cols-2 items-center justify-center"
                ),
            ),
            cls="p-4 md:p-6 pt-0 bg-black rounded-lg"
        ),
        cls="max-w-full md:max-w-7xl mx-auto rounded-lg border-2 backdrop-blur-sm text-white shadow-lg border-zinc-800",
        standard=True
    )

def get_information_display(extracted_info=None):
    return Div(
        Div(
            H3("CV Document Information", 
               cls="text-center text-xl md:text-2xl font-semibold leading-none tracking-tight text-white"),
            P("Extracted information from the uploaded CV document.",
              cls="text-center text-gray-400 text-xs md:text-sm mb-4 md:mb-6"),
            Div(
                *[
                    Div(
                        Div(
                            P(key + ":", cls="font-semibold text-blue-400 text-sm md:text-base" if not key == "Error" else "text-red-400 text-sm md:text-base"),
                            *[
                                P(f"{i+1}. {item}" if isinstance(value, list) else item or "Not found", 
                                  cls="ml-2 text-gray-300 text-xs md:text-sm" + (" mb-2" if isinstance(value, list) else ""))
                                for i, item in enumerate(value if isinstance(value, list) else [value])
                            ],
                            cls="flex-grow"
                        ),
                        Button(
                            Div(
                                Lucide("copy", cls="w-3 h-3 md:w-4 md:h-4"),
                                Div("Copy", cls="copy-tooltip text-gray-300 text-xs md:text-sm", id=f"tooltip-{key.lower().replace(' ', '-')}"),
                                cls="relative copy-btn hover:text-white text-white"
                            ),
                            onclick=f"copyToClipboard('{' '.join(value) if isinstance(value, list) else value or ''}', 'tooltip-{key.lower().replace(' ', '-')}')",
                            variant="ghost",
                            cls="p-1 md:p-2 hover:bg-blue-400/20 text-gray-300"
                        ),
                        cls="flex items-center justify-between mb-3 md:mb-4 p-3 md:p-4 border border-blue-400/30 rounded-lg bg-gradient-to-br from-blue-400/10 to-blue-400/5 hover:from-blue-400/20 hover:to-blue-400/10 transition-all duration-300 hover:border-blue-400/50 hover-lift" if not key == "Error" else "flex items-center justify-between mb-3 md:mb-4 p-3 md:p-4 border border-red-400/30 rounded-lg bg-gradient-to-br from-red-400/10 to-red-400/5 hover:from-red-400/20 hover:to-red-400/10 transition-all duration-300 hover:border-red-400/50 hover-lift"
                    )
                    for key, value in (extracted_info or {}).items()
                ] if extracted_info else [
                    P("Upload and process a CV to see extracted information.",
                      cls="text-gray-400 text-sm")
                ],
                cls="space-y-3 md:space-y-4"
            ),
            cls="w-full border-2 rounded-lg p-4 md:p-6 border-zinc-800"
        ),
        id="information-display",
        cls="flex flex-col gap-4 md:gap-6 mx-auto max-w-full md:max-w-7xl w-full"
    )

def get_rtc_chat_interface():
    return Div(
        Div(
            H3("Chat with CV", 
               cls="text-center text-xl md:text-2xl font-semibold leading-none tracking-tight text-white"),
            P("Ask questions using text or voice about the uploaded CV.",
              cls="text-center text-gray-400 text-xs md:text-sm mb-4 md:mb-6"),
            Div(
                Div(
                    Input(
                        type="text",
                        placeholder="Ask a question...",
                        id="chat-input",
                        cls="w-full p-2 text-sm md:text-base border border-zinc-700 rounded-lg bg-zinc-1000 placeholder-gray-400",
                        textarea=True,
                        onkeydown="if (event.key === 'Enter') { event.preventDefault(); sendChatMessage(); }"
                    ),
                    Button(
                        Lucide("mic", cls="w-3 h-3 md:w-4 md:h-4"),
                        Div(cls="recording-indicator"),
                        variant="outline",
                        id="toggleWebRTCButton",
                        cls="voice-chat-btn bg-blue-400/10 hover:bg-blue-400/20 border-white/40 hover:border-blue-400 relative hover:text-white text-white",
                        onClick="toggleVoiceChat()"
                    ),
                    cls="flex gap-2 md:gap-4 items-center"
                ),
                Div(
                    Button(
                        Div(
                            "Send",
                            cls="thinking-btn chat-btn-state items-center justify-center text-sm md:text-base"
                        ),
                        Div(
                            Lucide("loader", cls="w-3 h-3 md:w-4 md:h-4 mr-2 spinner"),
                            "Thinking...",
                            cls="loading-btn chat-btn-state items-center justify-center text-xs md:text-sm"
                        ),
                        id="chat-send",
                        variant="outline",
                        cls="bg-blue-400/10 hover:bg-blue-400/20 border-white/40 hover:border-blue-400 hover:text-white text-white",
                        onClick="sendChatMessage()"
                    ),
                    Button(
                        "Clear Chat",
                        variant="outline",
                        id="clear-chat",
                        cls="bg-red-400/10 hover:bg-red-400/20 border-red-400/30 hover:border-red-400 w-full hover:text-white text-white text-sm md:text-base",
                        onclick="clearChat()"
                    ),
                    cls="grid grid-cols-1 md:grid-cols-2 gap-2 md:gap-4"
                ),
                cls="space-y-3 md:space-y-4"
            ),
            Div(
                id="audio-output",
                cls="hidden transition-all duration-300 mt-3 md:mt-4 flex items-center justify-center"
            ),
            Div(
                id="chat-messages",
                cls="mt-3 md:mt-4 space-y-3 md:space-y-4"
            ),
            cls="w-full border-2 rounded-lg p-4 md:p-6 backdrop-blur-sm border-zinc-800"
        ),
        cls="flex flex-col gap-4 md:gap-6 mx-auto max-w-full md:max-w-7xl w-full"
    )