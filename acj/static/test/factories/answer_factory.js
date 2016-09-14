var objectAssign = require('object-assign');

var answerTemplate = {
    "id": null,
    "assignment_id": null,
    "user_id": null,
    "content": null,
    "comment_count": 0,
    "private_comment_count": 0,
    "public_comment_count": 0,
    "file": [],
    "scores": [],
    "user": {
        "id": null,
        "avatar": "8ddf878039b70767c4a5bcf4f0c4f65e",
        "displayname": null
    },
    "flagged": false,
    "created": "Fri, 22 Apr 2016 18:33:34 -0000",
}

function AnswerFactory() {};

AnswerFactory.prototype.generateAnswer = function (id, assignment_id, user, parameters) {
    var newAnswer = objectAssign({}, answerTemplate, parameters);
    newAnswer.id = id;
    newAnswer.assignment_id = assignment_id;
    newAnswer.user_id = user.id;
    newAnswer.user = {
        "id": user.id,
        "avatar": user.avatar,
        "displayname": user.displayname
    }

    return newAnswer;
};

module.exports = AnswerFactory;