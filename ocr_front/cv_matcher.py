from fasthtml.common import *
from shad4fast import *

def get_cv_jd_section():
    return Card(
        Div(
            Form(
                Div(
                    H3("Job Description Upload", 
                       cls="text-xl font-semibold text-white text-center"),
                    P("Upload the job description PDF file to compare with the CVs.",
                      cls="text-center text-gray-400 text-sm mb-6"),
                    Input(
                        type="file",
                        name="job_description",
                        accept="application/pdf",
                        cls="hidden",
                        id="file-upload-jd",
                        hx_post="/upload-jd",
                        hx_encoding="multipart/form-data",
                        hx_target="#upload-status",
                        hx_indicator="#upload-jd-indicator",
                        hx_trigger="change"
                    ),
                    Label(
                        Lucide("file-text", cls="w-10 h-10 mb-2 text-purple-400 float"),
                        "Upload Job Description PDF",
                        htmlFor="file-upload-jd",
                        cls="flex flex-col items-center text-white justify-center w-full h-32 border-2 border-dashed border-purple-400 rounded-lg cursor-pointer hover:bg-purple-400/5 glass hover-lift backdrop-blur-sm"
                    ),
                    id="jd-upload-container",
                    cls="mb-6"
                ),
                Div(
                    H3("CV Upload", 
                       cls="text-xl font-semibold text-white text-center"),
                    P("Upload the CV PDF files to compare with the job description.",
                      cls="text-center text-gray-400 text-sm mb-6"),
                    Input(
                        type="file",
                        name="cv_files",
                        accept="application/pdf",
                        multiple=True,
                        cls="hidden",
                        id="file-upload-cvs",
                        hx_post="/upload-cvs",
                        hx_encoding="multipart/form-data",
                        hx_target="#upload-status",
                        hx_indicator="#upload-cvs-indicator",
                        hx_trigger="change"
                    ),
                    Label(
                        Lucide("files", cls="w-10 h-10 mb-2 text-green-400 float"),
                        "Upload CV PDFs (Multiple)",
                        htmlFor="file-upload-cvs",
                        cls="flex flex-col items-center text-white justify-center w-full h-32 border-2 border-dashed border-green-400 rounded-lg cursor-pointer hover:bg-green-400/5 glass hover-lift backdrop-blur-sm"
                    ),
                    id="cv-upload-container",
                    cls="mb-6"
                ),
                Div(
                    Button(
                        Div(
                            "Compare CVs",
                            cls="compare-btn-text items-center justify-center"
                        ),
                        Div(
                            Lucide("loader", cls="w-4 h-4 mr-2 spinner"),
                            "Comparing...",
                            cls="flex compare-btn-loading hidden items-center justify-center"
                        ),
                        id="compare-btn",
                        type="button",
                        variant="outline",
                        cls="pulse w-full bg-blue-400/10 hover:bg-blue-400/20 border-blue-400/30 hover:border-blue-400 text-white hover:text-white",
                        hx_post="/compare-cvs",
                        hx_target="#matching-results",
                        hx_indicator="#compare-indicator"
                    ),
                    Button(
                        "Clear All",
                        variant="outline",
                        type="button",
                        cls="w-full bg-red-400/10 hover:bg-red-400/20 border-red-400/30 hover:border-red-400 text-white hover:text-white",
                        hx_post="/clear-matching",
                        hx_target="#matching-results"
                    ),
                    cls="grid grid-cols-2 gap-4"
                ),
            ),
            Div(id="upload-status"),
            cls="p-6 bg-black rounded-lg"
        ),
        cls="mx-auto rounded-lg border-2 backdrop-blur-sm border-zinc-800",
        standard=True
    )
    
def get_candidate_profile(i, match):
    """Generate a unified candidate profile display using FastHTML with collapsible content"""
    return Div(
        # Main container with gradient background
        Div(
            # Header section with name, match percentage, and collapse toggle
            Div(
                Div(
                    Div(
                        H3(f"#{i+1}: {match['cv_name']}", 
                           cls="text-2xl font-bold text-white"),
                        Lucide("chevron-down", 
                               cls="w-6 h-6 text-gray-400 transition-transform duration-200 transform hover:text-white cursor-pointer"),
                        cls="flex items-center gap-2"
                    ),
                    Div(
                        Span(
                            f"{match['match_percentage']}%",
                            cls=f"text-3xl font-bold {get_percentage_color(match['match_percentage'])}"
                        ),
                        P("Match Rate", cls="text-sm text-gray-400"),
                        cls="flex flex-col items-end"
                    ),
                    cls="flex justify-between items-center w-full"
                ),
                cls="flex justify-between items-center py-4 px-6 bg-zinc-900/50 rounded-lg border border-zinc-800 cursor-pointer hover:bg-zinc-900/70 transition-colors duration-200",
                onclick="toggleContent(this)"
            ),
            
            # Collapsible content container
            Div(
                # Requirements Match Section
                Div(
                    # Experience Match
                    Div(
                        P("Experience Match", cls="text-lg font-semibold text-white mb-1"),
                        Div(
                            P("Matches Requirements" if match['experience_match'] else "Does Not Match",
                                cls=f"{'text-green-400' if match['experience_match'] else 'text-red-400'}"),
                            Lucide("circle-check" if match['experience_match'] else "circle-x",
                                    cls=f"w-5 h-5 {'text-green-400' if match['experience_match'] else 'text-red-400'} ml-2"),
                            cls="flex items-center"
                        ),
                        cls="py-4 px-6 bg-zinc-900/50 rounded-lg border border-zinc-800"
                    ),
                    # Education Match
                    Div(
                        P("Education Match", cls="text-lg font-semibold text-white mb-1"),
                        Div(
                            P("Matches Requirements" if match['education_match'] else "Does Not Match",
                                cls=f"{'text-green-400' if match['education_match'] else 'text-red-400'}"),
                            Lucide("circle-check" if match['education_match'] else "circle-x",
                                    cls=f"w-5 h-5 {'text-green-400' if match['education_match'] else 'text-red-400'} ml-2"),
                            cls="flex items-center"
                        ),
                        cls="py-4 px-6 bg-zinc-900/50 rounded-lg border border-zinc-800"
                    ),
                    cls="grid grid-cols-2 gap-4 mb-6"
                ),
                
                # Skills Section
                Div(
                    H4("Skills Analysis", cls="text-lg font-semibold text-white mb-4"),
                    # Matching Skills
                    Div(
                        Div(
                            Lucide("check", cls="w-5 h-5 text-green-400"),
                            H5("Matching Skills", cls="text-base font-medium text-white ml-2"),
                            cls="flex items-center mb-2"
                        ),
                        Div(
                            *[
                                Span(
                                    skill,
                                    cls="px-3 py-1 bg-green-400/20 text-green-400 rounded-full text-sm border border-green-400/30 inline-block m-1"
                                ) for skill in match['matching_skills']
                            ],
                            cls="flex flex-wrap"
                        ),
                        cls="mb-4"
                    ),
                    # Missing Skills
                    Div(
                        Div(
                            Lucide("x", cls="w-5 h-5 text-red-400"),
                            H5("Missing Skills", cls="text-base font-medium text-white ml-2"),
                            cls="flex items-center mb-2"
                        ),
                        Div(
                            *[
                                Span(
                                    skill,
                                    cls="px-3 py-1 bg-red-400/20 text-red-400 rounded-full text-sm border border-red-400/30 inline-block m-1"
                                ) for skill in match['missing_skills']
                            ],
                            cls="flex flex-wrap"
                        )
                    ),
                    cls="py-4 px-6 bg-zinc-900/50 rounded-lg border border-zinc-800 mb-6"
                ),
                
                # Analysis Section
                Div(
                    Div(
                        H4("Full Analysis", cls="text-lg font-semibold text-white mr-2"),
                        Lucide("file-text", cls="w-5 h-5 text-purple-400"),
                        cls="flex items-center mb-4"
                    ),
                    P(match['detailed_analysis'],
                      cls="text-white text-sm"),
                    cls="py-4 px-6 bg-zinc-900/50 rounded-lg border border-zinc-800"
                ),
                
                cls="block mt-6 transition-all duration-300 overflow-hidden",
                id=f"content-{i}"
            ),
            
            cls="p-6 rounded-lg border-2 border-zinc-800 transition-all duration-300"
        ),
        cls="mb-6"
    )

def get_comparison_results(matches):
    """Generate the complete comparison results display"""
    return Card(
        CardHeader(
            CardTitle("CV Matching Results", cls="text-center text-2xl font-bold text-white mb-1"),
            P(f"Total Candidates Analyzed: {len(matches)}", 
              cls="text-center text-gray-400"),
            cls="bg-black rounded-lg"
        ),
        CardContent(
            *[get_candidate_profile(i, match) for i, match in enumerate(matches)],
            cls="space-y-4 bg-black rounded-lg"
        ),
        cls="mx-auto border-zinc-800 border-2 rounded-lg backdrop-blur-sm",
        standard=True
    )

def get_percentage_color(percentage):
    """Return appropriate color class based on the match percentage"""
    if percentage >= 70:
        return "text-green-400"
    elif percentage >= 40:
        return "text-yellow-400"
    return "text-red-400"