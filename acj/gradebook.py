from __future__ import division

from bouncer.constants import MANAGE
from flask import Blueprint, jsonify
from flask.ext.login import login_required, current_user
from flask.ext.restful import Resource
from .authorization import require
from .models import Courses, PostsForQuestions, UserTypesForCourse, Users, CoursesAndUsers, Judgements, \
    AnswerPairings, CriteriaAndPostsForQuestions, PostsForAnswersAndPostsForComments, PostsForAnswers

from .util import new_restful_api
from .core import event
import copy


# First declare a Flask Blueprint for this module
gradebook_api = Blueprint('gradebook_api', __name__)
# Then pack the blueprint into a Flask-Restful API
api = new_restful_api(gradebook_api)

# events
on_gradebook_get = event.signal('GRADEBOOK_GET')


# declare an API URL
# /
class GradebookAPI(Resource):
    @login_required
    def get(self, course_id, question_id):
        course = Courses.query.get_or_404(course_id)
        question = PostsForQuestions.query.get_or_404(question_id)
        require(MANAGE, question)

        # get all students in this course
        student_type = UserTypesForCourse.query.filter_by(name=UserTypesForCourse.TYPE_STUDENT).first()
        students = Users.query.join(CoursesAndUsers).filter(
            CoursesAndUsers.courses_id == course.id, CoursesAndUsers.usertypesforcourse_id == student_type.id).all()

        # get all judgements for this question
        judgements = Judgements.query.join(AnswerPairings).filter(
            AnswerPairings.questions_id == question.id).all()

        # how many judgements has each user done
        num_judgements_by_user_id = {}
        for judgement in judgements:
            num_judgements = num_judgements_by_user_id.get(judgement.users_id, 0)
            num_judgements += 1
            num_judgements_by_user_id[judgement.users_id] = num_judgements

        # we want only the count for judgements by current students in the course
        criteria = CriteriaAndPostsForQuestions.query.filter_by(questions_id=question.id, active=True).all()
        num_judgements_per_student = {}
        for student in students:
            num_judgements_per_student[student.id] = num_judgements_by_user_id.get(student.id, 0) / len(criteria)

        # count number of answers each student has submitted
        num_answers_by_user_id = {}
        scores_by_user_id = {}
        flagged_by_user_id = {}
        init_scores = {c.id: 'Not Evaluated' for c in criteria}
        for answer in question.answers:
            num_answers = num_answers_by_user_id.get(answer.post.users_id, 0)
            num_answers += 1
            num_answers_by_user_id[answer.post.users_id] = num_answers

            # scores - assume one answer for each user for now
            scores_by_user_id[answer.post.users_id] = copy.deepcopy(init_scores)
            for score in answer.scores:
                # skip scores for inactive criteria
                if score.criteriaandquestions_id not in init_scores:
                    continue
                scores_by_user_id[answer.post.users_id][score.criteriaandquestions_id] = round(score.normalized_score, 3)

            flagged_by_user_id[answer.post.users_id] = 'Yes' if answer.flagged else 'No'

        # we want only answers submitted by students
        num_answers_per_student = {}
        for student in students:
            num_answers_per_student[student.id] = num_answers_by_user_id.get(student.id, 0)

        include_self_eval = False
        num_selfeval_per_student = {}
        num_selfeval_by_user_id = {}
        if question.selfevaltype_id:
            include_self_eval = True
            # assuming self-evaluation with no comparison
            comments = PostsForAnswersAndPostsForComments.query.filter_by(selfeval=True) \
                .join(PostsForAnswers).filter_by(questions_id=question_id).all()

            for comment in comments:
                num_eval = num_selfeval_by_user_id.get(comment.users_id, 0)
                num_eval += 1
                num_selfeval_by_user_id[comment.users_id] = num_eval

            for student in students:
                num_selfeval_per_student[student.id] = num_selfeval_by_user_id.get(student.id, 0)

        # {'gradebook':[{user1}. {user2}, ...]}
        # user id, username, first name, last name, answer submitted, judgements submitted
        gradebook = []
        no_answer = {c.id: 'No Answer' for c in criteria}
        for student in students:
            score = scores_by_user_id.get(student.id, no_answer)
            entry = {
                'userid': student.id,
                'displayname': student.displayname,
                'firstname': student.firstname,
                'lastname': student.lastname,
                'num_answers': num_answers_per_student[student.id],
                'num_judgements': num_judgements_per_student[student.id],
                'scores': score,
                'flagged': flagged_by_user_id.get(student.id, 'No Answer')
            }
            if include_self_eval:
                entry['num_selfeval'] = num_selfeval_per_student[student.id]
            gradebook.append(entry)

        ret = {
            'gradebook': gradebook,
            'num_judgements_required': question.num_judgement_req,
            'include_self_eval': include_self_eval
        }

        on_gradebook_get.send(
            self,
            event_name=on_gradebook_get.name,
            user=current_user,
            course_id=course_id,
            data={'question_id': question_id})

        return jsonify(ret)
api.add_resource(GradebookAPI, '')
