from dataclasses import dataclass

@dataclass
class QuoraQuestionsPair:
        question1 : str 
        question2 : str
        is_duplicate : int